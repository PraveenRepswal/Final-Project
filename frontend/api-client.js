(function (global) {
  const API_BASE_STORAGE_KEY = "ai_job_assistant_api_base";
  const PROVIDER_STORAGE_KEY = "ai_job_assistant_provider";
  const RESUME_TEXT_STORAGE_KEY = "ai_job_assistant_resume_text";
  const RESUME_DATA_STORAGE_KEY = "ai_job_assistant_resume_data";

  function defaultApiBase() {
    if (global.location.protocol === "http:" || global.location.protocol === "https:") {
      return `${global.location.protocol}//${global.location.hostname}:8000`;
    }
    return "http://127.0.0.1:8000";
  }

  function getApiBase() {
    return localStorage.getItem(API_BASE_STORAGE_KEY) || defaultApiBase();
  }

  function setApiBase(baseUrl) {
    if (!baseUrl) {
      return;
    }
    localStorage.setItem(API_BASE_STORAGE_KEY, String(baseUrl).trim().replace(/\/$/, ""));
  }

  function normalizeProvider(provider) {
    const value = String(provider || "").trim().toLowerCase();
    if (value === "gemini") {
      return "gemini";
    }
    if (value === "llama.cpp" || value === "llama_cpp" || value === "llamacpp") {
      return "llama.cpp";
    }
    return "ollama";
  }

  function getProvider() {
    return normalizeProvider(localStorage.getItem(PROVIDER_STORAGE_KEY));
  }

  function setProvider(provider) {
    localStorage.setItem(PROVIDER_STORAGE_KEY, normalizeProvider(provider));
  }

  function defaultModelForProvider(provider) {
    const selectedProvider = normalizeProvider(provider);
    if (selectedProvider === "gemini") {
      return "gemini-2.5-flash";
    }
    if (selectedProvider === "llama.cpp") {
      return "local-model";
    }
    return "qwen3.5:2b";
  }

  function getInferenceConfig(overrides) {
    const baseProvider = getProvider();
    const config = {
      provider: baseProvider,
      model: defaultModelForProvider(baseProvider),
      think: true,
    };

    if (overrides && typeof overrides === "object") {
      Object.assign(config, overrides);
      config.provider = normalizeProvider(config.provider);
      if (!config.model) {
        config.model = defaultModelForProvider(config.provider);
      }
      if (typeof config.think !== "boolean") {
        config.think = true;
      }
      return config;
    }

    return config;
  }

  function appendInferenceFields(formData, overrides) {
    const config = getInferenceConfig(overrides);
    formData.append("provider", config.provider);
    formData.append("model", config.model);
    formData.append("think", String(config.think));
    return config;
  }

  async function request(path, options) {
    const opts = options || {};
    const method = opts.method || "GET";
    const isFormData = !!opts.isFormData;
    const headers = Object.assign({}, opts.headers || {});
    let body = opts.body;

    if (body && !isFormData && !(body instanceof Blob) && typeof body !== "string") {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(body);
    }

    const response = await fetch(`${getApiBase()}${path}`, {
      method,
      headers,
      body,
    });

    const rawText = await response.text();
    let data = null;

    if (rawText) {
      try {
        data = JSON.parse(rawText);
      } catch (error) {
        data = rawText;
      }
    }

    if (!response.ok) {
      const message =
        data && typeof data === "object" && data.detail
          ? data.detail
          : `Request failed (${response.status})`;
      throw new Error(message);
    }

    return data;
  }

  function setResumeContext(rawText, resumeData) {
    localStorage.setItem(RESUME_TEXT_STORAGE_KEY, rawText || "");
    localStorage.setItem(RESUME_DATA_STORAGE_KEY, JSON.stringify(resumeData || {}));
  }

  function getResumeText() {
    return localStorage.getItem(RESUME_TEXT_STORAGE_KEY) || "";
  }

  function getResumeData() {
    try {
      return JSON.parse(localStorage.getItem(RESUME_DATA_STORAGE_KEY) || "{}");
    } catch (error) {
      return {};
    }
  }

  global.AIJobAssistantAPI = {
    getApiBase,
    setApiBase,
    getProvider,
    setProvider,
    defaultModelForProvider,
    getInferenceConfig,
    appendInferenceFields,
    request,
    setResumeContext,
    getResumeText,
    getResumeData,
  };
})(window);
