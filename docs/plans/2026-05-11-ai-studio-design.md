# Design: AI Studio & Prompt Enhancement Engine

## Overview
This feature introduces an "AI Studio" to the Link project, allowing users to leverage Large Language Models (LLMs) to enhance their ComfyUI prompts. Users can manage multiple AI providers, curate a library of system prompts categorized by Image/Video, and configure workflows to use these enhancements interactively via Discord and the Dashboard.

## 1. Storage Layer

### 1.1 Global AI Configuration (`src/workflows/ai_config.yaml`)
Stores provider settings and active defaults.
- **Structure**:
  - `active_provider`: ID of the currently used LLM provider.
  - `providers`: Dictionary of provider configurations (Model, Base URL).
- **Security**: API keys are stored in the `.env` file and accessed via standard environment variables.

### 1.2 System Prompt Library (`src/workflows/prompts.json`)
A collection of user-defined system prompts.
- **Entry Fields**:
  - `id`: Unique identifier.
  - `name`: Human-readable name.
  - `category`: `image` or `video`.
  - `content`: The actual system prompt text.

### 1.3 Workflow Manifest Update (`manifest.yaml`)
Each workflow can opt-in to AI enhancement.
- **Fields**:
  - `ai_prompt`:
    - `enabled`: Boolean toggle.
    - `category`: `image` | `video`.
    - `prompt_id`: ID of the system prompt to use.
    - `target_input`: The ID of the workflow input field that will receive the enhanced text.

## 2. Frontend Components

### 2.1 AI Studio Tab (`AiStudio.tsx`)
A new primary tab in the dashboard for centralized AI management.
- **Provider Management**: Toggle between providers (Gemini, OpenAI, Ollama, etc.) and configure their model/endpoint.
- **Prompt Library Manager**: A CRUD interface to manage system prompts, with filtering by category.
- **Default Presets**: Set global defaults for new workflows.

### 2.2 Architect View Enhancements
- **AI Bar**: A new header section for workflows to configure AI settings.
- **Target Selection**: In the List View, users can designate a specific text input as the "AI Target."

### 2.3 Mission Control Updates
- Add UI fields to the Environment panel for managing LLM API keys in the `.env` file.

## 3. Backend API Service

- **Configuration Endpoints**:
  - `GET /api/ai/config`: Returns the current `ai_config.yaml`.
  - `POST /api/ai/config`: Updates the `ai_config.yaml`.
  - `GET /api/ai/prompts`: Returns the list of system prompts.
  - `POST /api/ai/prompts`: Updates/Adds a system prompt.
- **Enhancement Endpoint**:
  - `POST /api/ai/enhance`: Takes a `user_prompt` and `prompt_id`, hits the configured LLM provider, and returns the enhanced prompt text.

## 4. Discord Bot Integration

### 4.1 The Enhancement Modal
When a workflow with AI enabled is triggered:
1. The bot defers the interaction and calls the backend `/api/ai/enhance` endpoint.
2. The bot presents a Modal to the user containing the enhanced prompt.
3. The user can "Continue" to accept the enhancement or "Edit" to make manual changes.
4. The pipeline then proceeds to the LoRA picker (if applicable) and final generation.

## 5. Providers to Support
- **Cloud**: Gemini (Vertex/Google), OpenAI, Anthropic, Grok.
- **Local**: Ollama, LM Studio, vLLM.
- **Compatibility**: Standardize on OpenAI-compatible API formats where possible (especially for Ollama/LMStudio/vLLM).
