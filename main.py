"""AI Job Assistant - Resume Parser & ATS Scorer & RAG Chat

Phase 3: Chat With Resume (RAG)
Includes Resume Parsing, ATS Scoring, and Interactive Chat.
Fixed for Gradio 6.0 and updated Google GenAI SDK.
"""

import logging
import json
import plotly.graph_objects as go
import gradio as gr
from dotenv import load_dotenv

from resume_parser import ResumeParser, ResumeData
from resume_parser.ats_scorer import ATSScorer, ATSResult
from resume_parser.ai_extractor import check_ollama_connection
try:
    from resume_parser.rag_engine import RAGEngine
except ImportError:
    RAGEngine = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global storage
current_resume_data = None
rag_engine_instance = None

def get_rag_engine():
    """Singleton accessor for RAG Engine."""
    global rag_engine_instance
    if rag_engine_instance is None:
        if RAGEngine:
            try:
                rag_engine_instance = RAGEngine()
            except Exception as e:
                logger.error(f"Failed to init RAG Engine: {e}")
                return None
        else:
            logger.warning("RAGEngine class not imported (dependencies missing?)")
            return None
    return rag_engine_instance

def parse_resume(file, provider: str, model: str):
    """
    Parse uploaded resume and return structured JSON data.
    Also indexes text for RAG.
    """
    global current_resume_data
    
    if file is None:
        return json.dumps({"error": "Please upload a resume file"}, indent=2), "", ""
    
    try:
        selected_model = model
        if provider == "gemini":
            if not selected_model or selected_model.startswith("qwen"):
                selected_model = "gemini-2.5-flash"
        
        parser = ResumeParser(model=selected_model, provider=provider)
        logger.info(f"Processing file: {file.name}")
        
        result_tuple, raw_text = parser.parse(file.name)
        
        if isinstance(result_tuple, tuple):
            resume_data, debug_raw = result_tuple
        else:
            resume_data = result_tuple
            debug_raw = ""
            
        debug_info = parser.get_debug_info()
        
        if resume_data:
            current_resume_data = resume_data
            data_dict = resume_data.model_dump(exclude_none=False)
            
            rag = get_rag_engine()
            if rag and raw_text:
                rag.ingest_text(raw_text, metadata={"source": file.name})
                debug_info += "\n\n[RAG] Resume indexed for chat."
            
            return json.dumps(data_dict, indent=2, ensure_ascii=False), raw_text, debug_info
        else:
            return json.dumps({"error": "AI extraction failed"}, indent=2), raw_text, debug_info
            
    except Exception as e:
        logger.error(f"Error parsing resume: {e}", exc_info=True)
        return json.dumps({"error": str(e)}, indent=2), "", ""

def calculate_ats_score(job_description: str, provider: str, model: str):
    """Calculate ATS score and generate visualizations."""
    global current_resume_data
    
    if not current_resume_data:
        return (None, None, None, "⚠️ Please parse a resume first.", "")
    
    if not job_description or len(job_description) < 50:
        return (None, None, None, "⚠️ Please enter a valid Job Description.", "")
    
    try:
        selected_model = model
        if provider == "gemini": selected_model = "gemini-2.5-flash"
            
        scorer = ATSScorer(model=selected_model, provider=provider)
        result = scorer.calculate_score(current_resume_data, job_description)
        
        # 1. Gauge Chart
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = result.score,
            title = {'text': "ATS Score"},
            gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "darkblue"},
                     'steps': [{'range': [0, 50], 'color': "lightgray"}, {'range': [50, 80], 'color': "gray"}],
                     'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}}
        ))
        
        # 2. Radar Chart
        categories = list(result.breakdown.keys())
        max_values = {"Keywords": 40, "Skills": 30, "Formatting": 10, "Education": 10, "Experience": 10}
        normalized_values = [(result.breakdown[k] / max_values.get(k, 10)) * 100 for k in categories]
        
        fig_radar = go.Figure(data=go.Scatterpolar(r=normalized_values, theta=categories, fill='toself'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False, title="Category Performance (%)")
        
        # 3. Text Outputs
        missing_kw_md = "### ❌ Missing Keywords\n"
        missing_kw_md += " ".join([f"`{kw}`" for kw in result.missing_keywords]) if result.missing_keywords else "✅ None!"
            
        suggestions_md = "### 💡 Suggestions\n" + ("\n".join([f"- {s}" for s in result.suggestions]) if result.suggestions else "Looks good!")
            
        return fig_gauge, fig_radar, missing_kw_md, suggestions_md, json.dumps(result.to_dict(), indent=2)
        
    except Exception as e:
        logger.error(f"Error calculating ATS score: {e}", exc_info=True)
        return None, None, None, f"Error: {str(e)}", ""

def chat_response(message, history, provider, model):
    """
    Handle RAG Chat interaction.
    """
    rag = get_rag_engine()
    if not rag:
        yield "⚠️ Chat engine not initialized (Parsing resume might be required or deps missing).", "", "", ""
        return

    if not rag.vector_store:
         yield "⚠️ No resume content found. Please parse a resume first!", "", "", ""
         return

    try:
        selected_model = model
        if provider == "gemini":
             selected_model = "gemini-2.5-flash"
             
        # Prepare all chunks for display
        all_chunks_str = json.dumps(rag.all_chunks, indent=2) if rag.all_chunks else "[]"

        for chunk, context, prompt in rag.query(message, provider=provider, model=selected_model):
            yield chunk, context, prompt, all_chunks_str
            
    except Exception as e:
        yield f"Error: {str(e)}", "", "", ""

def check_system_status() -> str:
    status = "✅ System Ready\n" if check_ollama_connection() else "❌ Ollama Connection Failed\n"
    if get_rag_engine():
        status += "✅ RAG Engine Loaded"
    else:
        status += "⏳ RAG Engine Loading/Missing"
    return status

def create_demo_interface():
    custom_css = ".gradio-container { max-width: 1200px !important; } .output-json { font-family: monospace; font-size: 12px; }"
    
    # Removed theme and css from Blocks to avoid warning in Gradio 6.0
    with gr.Blocks(title="AI Job Assistant") as demo:
        gr.Markdown("# 🤖 AI Job Assistant")
        
        with gr.Row():
            status_btn = gr.Button("🔍 Check System Status", variant="secondary")
            status_output = gr.Textbox(label="Status", lines=2, interactive=False)
            status_btn.click(fn=check_system_status, outputs=status_output)
            
        with gr.Row():
            provider_input = gr.Dropdown(label="Provider", choices=["ollama", "gemini"], value="ollama")
            model_input = gr.Textbox(label="Model", value="qwen3:4b", placeholder="qwen3:4b or gemini-2.5-flash")
        
        def _update_model(provider):
            return "gemini-2.5-flash" if provider == "gemini" else "qwen3:4b"
        provider_input.change(_update_model, inputs=provider_input, outputs=model_input)
            
        with gr.Tabs():
            with gr.TabItem("📄 Resume Parser"):
                with gr.Row():
                    with gr.Column(scale=1):
                        file_input = gr.File(label="Upload Resume", file_types=[".pdf", ".docx"])
                        parse_btn = gr.Button("🚀 Parse Resume", variant="primary", size="lg")
                    with gr.Column(scale=2):
                        with gr.Tabs():
                            with gr.TabItem("Structured Data"): json_output = gr.Code(label="JSON", language="json", lines=20)
                            with gr.TabItem("Raw Text"): text_output = gr.Textbox(label="Text", lines=20)
                            with gr.TabItem("Debug"): debug_output = gr.Textbox(label="Debug Info", lines=20)
                parse_btn.click(parse_resume, inputs=[file_input, provider_input, model_input], outputs=[json_output, text_output, debug_output])
            
            with gr.TabItem("🎯 ATS Scorer"):
                gr.Markdown("### Calculate ATS Score based on Job Description")
                jd_input = gr.TextArea(label="Paste Job Description Here", lines=10)
                score_btn = gr.Button("📊 Calculate Score", variant="primary", size="lg")
                with gr.Row():
                    with gr.Column(): gauge_chart = gr.Plot(label="Overall Score")
                    with gr.Column(): radar_chart = gr.Plot(label="Breakdown")
                with gr.Row():
                    missing_kw_output = gr.Markdown(label="Missing Keywords")
                    suggestions_output = gr.Markdown(label="Suggestions")
                with gr.Accordion("Raw Scoring Data", open=False):
                    ats_raw_output = gr.Code(language="json")
                score_btn.click(calculate_ats_score, inputs=[jd_input, provider_input, model_input], 
                                outputs=[gauge_chart, radar_chart, missing_kw_output, suggestions_output, ats_raw_output])

            # TAB 3: CHAT (RAG)
            with gr.TabItem("💬 Chat with Resume"):
                gr.Markdown("### Ask questions about the uploaded resume")
                
                # Expanders for RAG Debugging
                with gr.Accordion("📚 Retrieved Context", open=False):
                    context_output = gr.Markdown(label="Chunks Used")
                
                with gr.Accordion("🤖 Full Prompt", open=False):
                    prompt_output = gr.Code(label="Prompt Sent to LLM", language="markdown")

                with gr.Accordion("📂 All Document Chunks", open=False):
                    chunks_output = gr.Code(label="All Text Splits", language="json")
                
                # Chat Interface with additional outputs
                chat_interface = gr.ChatInterface(
                    fn=chat_response,
                    additional_inputs=[provider_input, model_input],
                    additional_outputs=[context_output, prompt_output, chunks_output],
                    title="Resume Chat"
                )

    return demo, custom_css  # Return CSS to pass to launch()

def main():
    demo, css = create_demo_interface()
    # Pass css and theme to launch() as requested by Gradio 6.0 warning
    demo.launch(server_name="127.0.0.1", server_port=7861, share=False, css=css) # theme arg might not be in launch yet, checking docs... 
    # Actually, theme IS usually in Blocks in Gradio 4/5. 
    # If Gradio 6 moved it, I will just suppress it for now by not setting it in launch (using default) 
    # or pass it if I knew the API. Safe bet: define Blocks(..., theme=...) and ignore warning if it works, 
    # BUT warning said "theme, css" moved to launch. 
    # Let's try passing 'css' to launch. 'theme' object might be harder to pass if launch expects name string vs object.
    # Leaving theme default for safety.

if __name__ == "__main__":
    main()
