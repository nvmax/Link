1. High-Level Architecture (Separation of Concerns)To keep this modular, we should treat the system as three distinct layers that communicate via internal APIs or events:LayerResponsibilityPrimary Tech/LogicInterface LayerDiscord interaction, command parsing, and user feedback.discord.py or nextcordOrchestration LayerTask queuing, state management, and payload building.asyncio, Redis or SQLiteIntegration LayerDirect communication with the ComfyUI WebSocket/API.aiohttp, websockets

2. Core Feature BrainstormBackend & LogicDynamic Workflow Mapping: Instead of hardcoding prompts, use a "Template" system where JSON workflows from ComfyUI are stored as templates. The bot fills in specific nodes (e.g., Load Checkpoint, CLIP Text Encode) based on Discord arguments.Job Queue & Concurrency: Since image/video generation is resource-intensive, implement a queue.Feature: Priority lanes for different users (e.g., "Supporter" vs "Standard").Session Management: Maintain a "state" for each user so they can iterate on an image (e.g., "Vary Strong" or "Upscale") without re-uploading everything.The Discord Interface (Frontend)Slash Command Suite: * /gen [prompt] [workflow_name] [aspect_ratio]/video [prompt] [motion_bucket]Interactive Components: Use Discord Buttons and Select Menus for post-generation actions (e.g., [Upscale], [Download JSON], [Re-roll]).Real-time Progress: Use the ComfyUI WebSocket to update a Discord embed with a progress bar (e.g., [▓▓▓░░] 60%).

3. Project Structure (PEP 8 & Modular)Following a clean Pythonic structure will make this easy to upgrade:Plaintextproject_root/
├── src/
│   ├── bot/                # Discord client logic & cogs
│   ├── comfy/              # ComfyUI API & WebSocket handlers
│   ├── core/               # Shared config, logging, and constants
│   ├── database/           # Persistence (settings, user history)
│   └── workflows/          # JSON templates for ComfyUI
├── tests/                  # Unit and integration tests
├── .env                    # Secrets and API endpoints
├── main.py                 # Entry point
└── requirements.txt

4. Advanced "Easy Upgrade" FeaturesPlugin System for Nodes: Create a way to register "Parsers" for specific ComfyUI custom nodes (like IP-Adapter or ControlNet) without touching the core bot logic.Multi-Instance Support: Allow the bot to load-balance across multiple local ComfyUI instances if you have multiple GPUs.Auto-venv Script: Since you prefer venv, we should include a setup.py or Makefile that handles the environment and dependency verification automatically.

STEP 2

1. The "Workflow-Agile" LogicTo avoid rewriting code for every new workflow, you can use a Manifest System. Each ComfyUI JSON file in your workflows/ folder should have a corresponding .yaml or .json manifest.The Manifest ConceptWhen you drop in cinematic_video.json, you also drop in cinematic_video.yaml:YAMLworkflow_name: "Cinematic Video"
description: "Generates high-fidelity 5-second clips"
discord_command: "video"
mapping:
  prompt_node: "6"
  negative_node: "7"
  model_node: "10"
  sampler_node: "3"
  video_length_node: "25"
inputs:
  - id: "prompt"
    type: "text"
    label: "What do you want to see?"
  - id: "motion"
    type: "slider"
    min: 1
    max: 10
The bot reads this manifest to dynamically build the Discord Modal. If a workflow doesn't have a "length" mapping, that field simply doesn't appear in the modal.

2. Database Schema (The "Source of Truth")Since you want a detailed history, a relational database (PostgreSQL or SQLite) is best to track the relationships between users, workflows, and files.TableKey FieldsGenerationsgen_id, user_id, workflow_used, status, timestamp, discord_msg_idParametersgen_id, key (e.g., prompt), value (e.g., "A cyberpunk cat"), type (input/output)Assetsasset_id, gen_id, file_path, file_type (img/vid/lora), original_filenameWorkflowsversion_hash, filename, is_active, last_updated

3. Unified Progress TrackingTo prevent custom code for every progress bar, you can implement a WebSocket Observer.Intercept: The comfy/ module listens to the /history and execution_proccessing endpoints via WebSockets.Calculate: ComfyUI sends "current node" vs "total nodes." You can calculate a percentage based on (current_node_index / total_nodes) * 100.Throttled Update: Discord has rate limits. Instead of updating for every % change, the Orchestrator should only update the Discord Embed every 2 seconds or every 10% change.

4. Implementation Plan: Modular StructureFollowing PEP 8 and Separation of Concerns:
Phase 1: The Core Bridge (The "Plumbing")ComfyClient Class: An async wrapper using aiohttp to send the JSON payloads and websockets to listen for progress/output.Workflow Parser: A service that takes a Mapping + User Inputs and injects them into the raw ComfyUI JSON template.
Phase 2: The Interface (The "UX")Dynamic Modal Builder: A function that generates a discord.ui.Modal on the fly based on the YAML manifest.Asset Manager: Logic to handle Discord attachments (e.g., if a user uploads two images to "merge," the bot downloads them to a temporary /input folder for ComfyUI).
Phase 3: The Brain (The "Persistence")CRUD Operations: Logic to save every generation and its metadata. This allows for features like /history or /retry.Cleanup Service: A background task to delete old local files to save disk space after they’ve been uploaded to Discord.

5. Brainstorming: Image Editing & MergingFor the "Edit" and "Merge" features, we can use Action Rows:Merge: Command /merge triggers a modal asking for the "Blend Ratio." The bot expects two image attachments.Edit: When a generation is finished, the Discord message includes an [Edit] button. Clicking it opens a modal to change the prompt or strength, using the previous generation's seed and image as a starting point.

Step 3

1. The Project BlueprintThe "Workflow Manager" (Core Logic)Instead of hardcoding, we use a Registry Pattern.Scanner: On startup, a service reads all .json (ComfyUI) and .yaml (Manifest) pairs.Validator: It checks that the mapping in the YAML actually points to node IDs that exist in the JSON.Injector: A utility function that takes user_input and deep-updates the JSON dictionary before sending it to the ComfyUI API.The "Unified Interface" (UX)To handle the "Modal" requirement, we’ll create a DynamicModal class that inherits from discord.ui.Modal.It accepts a list of "Field" objects defined in your YAML.It automatically handles the on_submit by gathering all fields and passing them to the Job Queue.

2. Technical Architecture & Data FlowTo maintain the Separation of Concerns, the data should flow like this:Interaction: User triggers /gen_x.Modal: Bot serves a Modal based on the x.yaml manifest.Persistence: The moment the user hits "Submit," a row is created in the Generations Table with a PENDING status.Queue: the Job is added to an internal asyncio.Queue.Execution: The ComfyWorker picks it up, uploads any attachments (for merges/edits), and hits the /prompt endpoint.Feedback: The WebsocketListener catches progress and updates the specific discord_msg_id stored in the DB.

3. Database Schema (Detailed)Since you want high-level tracking for prompts, LoRAs, and settings, I recommend a JSONB (or flat JSON string in SQLite) column for "metadata" to keep it flexible, while keeping core fields indexed.Table: generationsTypeDescriptionidUUID (PK)Unique ID for the gen.user_idBigIntDiscord User ID.workflow_typeStringe.g., "txt2vid", "img_merge".statusEnumPENDING, PROCESSING, COMPLETED, FAILED.input_paramsJSONStores prompt, seed, cfg, etc.output_urlStringPath to the local file or Discord CDN link.parent_idUUID(Optional) Links to the original image for "Edits".

4. The "Progress Bar" LogicTo keep it unified and PEP 8 clean, we’ll use a ProgressManager class.Pythonclass ProgressManager:
    def __init__(self, total_steps):
        self.total_steps = total_steps
        self.current_step = 0

    def format_bar(self, current_step):
        percentage = min(100, int((current_step / self.total_steps) * 100))
        filled = int(percentage / 10)
        bar = "█" * filled + "░" * (10 - filled)
        return f"**Progress:** [{bar}] {percentage}%"
The worker will update the message embed with this string every time the WebSocket broadcasts a progress event.

5. Directory Structure for PEP 8 ModularityPlaintext/discord-comfy-tool
├── data/               # SQLite DB and local image storage
├── workflows/          # .json and .yaml pairs
│   ├── base_txt2img.json
│   └── base_txt2img.yaml
├── src/
│   ├── api/            # ComfyUI API & WebSocket logic
│   ├── bot/            # Discord Cogs and Modal logic
│   ├── database/       # Models and DB sessions
│   ├── utils/          # Image processing & Progress bar
│   └── manager.py      # The "Workflow Registry" scanner
├── main.py             # Entry point (initializes DB and Bot)
└── requirements.txt
Brainstorming the "Edit/Merge" Logic:For the Merge feature, how should we handle the "Model" selection?Option A: You have a specific folder of "Merge Models" the bot scans and presents as a Select Menu in the modal.Option B: It uses whatever model is currently loaded in the ComfyUI workflow.Given your preference for modularity, I'd suggest Option A—letting the YAML manifest define a model_list source so the user can choose from your local checkpoints via a dropdown in Discord.Does this structure align with how you want to handle the file organization, or should we nest the workflows differently?

Step 4

1. The Dynamic Injection Strategy
We will create an Injector service. This service doesn't care about the workflow's structure; it only cares about the Mapping Dictionary.

How it works:
The Python Core defines standard "Internal Keys" (e.g., primary_prompt, seed_value, model_name).

The YAML Manifest acts as the translator.

The Injector performs a "Deep Search and Replace" on the JSON dictionary.

Example YAML for Workflow A:
YAML
# In this workflow, the prompt is node 10
mappings:
  primary_prompt: ["10", "inputs", "text"]
  seed_value: ["3", "inputs", "seed"]
Example YAML for Workflow B:
YAML
# In this workflow, the prompt is node 4 (different node ID!)
mappings:
  primary_prompt: ["4", "inputs", "text"]
  seed_value: ["18", "inputs", "noise_seed"]
The Python Logic stays the same:
json_data[mapping['primary_prompt']] = user_input_text

2. Handling Complex Logic (The "Logic Hub")
Some workflows require more than just a text swap (e.g., an image merge needs two image paths). To handle this without writing custom code for every workflow, we use Input Types.

In your YAML, you define the "Type" of data the node expects:

type: "image_upload" -> Bot knows to download the Discord attachment and put the local path into the JSON.

type: "slider" -> Bot converts the Discord text input to an integer/float.

type: "lora_select" -> Bot looks up your local LoRA folder and populates a dropdown.

3. The Implementation Plan: "The Orchestrator"
To keep things modular, here is the suggested structure for the Processing Logic:

A. The WorkflowRegistry (Service)
Responsibility: On boot, scans the folder. It stores a dictionary of CommandName -> {JSON_Template, YAML_Manifest}.

Benefit: Adding a new workflow is as simple as adding two files. No main.py changes needed.

B. The PayloadBuilder (Utility)
Responsibility: This is the "brain." It takes the raw user input from the Discord Modal and the Mapping from the YAML.

Logic:

It iterates through the mappings in the YAML.

It finds the corresponding node in the JSON.

It applies "Sanitizers" (e.g., ensuring a seed is a number, not a string).

C. The AssetManager (Utility)
Responsibility: Handles the "Front-end to Back-end" file transfer.

Logic: If a workflow requires an image input, this service grabs the image from the Discord message, saves it to comfyui/input/, and returns the filename for injection.

Step 5

Implementation Steps
I suggest we tackle the PayloadBuilder first, as it’s the heart of the "Self-Updating" system.

Step 1: The Core Data Model
We'll define a Python class (using pydantic or standard dataclasses) to represent a "Job."

Python
from dataclasses import dataclass
from typing import Any, Dict

@dataclass
class GenerationJob:
    job_id: str
    user_id: int
    workflow_name: str
    user_inputs: Dict[str, Any]  # e.g. {"prompt": "A forest", "seed": 123}
    status: str = "pending"
Step 2: The Injection Method
We need a function that can reach deep into the nested ComfyUI JSON (which is just a massive Python Dictionary) and swap values based on the YAML paths.

step 5

1. The "Prompt Enhancer" Service Logic
We should create an LLMProvider interface. This allows you to swap between LM Studio, Ollama, or OpenAI without changing the bot's core logic.

Enhancement Workflow:
Input: User fills out the initial Discord Modal with a basic prompt.

Trigger: User clicks an "Enhance ✨" button (or toggles an "Auto-Enhance" setting).

Process: * The bot sends the raw prompt + a System Prompt (defined in your config) to your local LLM (Ollama/LM Studio).

The LLM returns a descriptive, detailed version.

Edit Step: The bot serves a Second Modal containing the enhanced text, allowing the user to tweak it before the final ComfyUI execution.

2. Updated YAML Schema: Enhancer Integration
We can add an enhancer section to your YAML to tell the bot which system prompt to use for that specific workflow.

YAML
workflow_metadata:
  name: "Cinematic Landscape"
  
enhancer_settings:
  enabled: true
  system_prompt: "Act as a professional cinematographer. Expand the user's prompt into a detailed 8k description focusing on lighting, atmosphere, and camera lens (e.g., 35mm, anamorphic)."
  provider: "ollama"  # or "lmstudio", "openai"
  model: "llama3:8b"

node_mappings:
  primary_prompt: ["6", "inputs", "text"]

3. Implementation Plan: The "Double-Modal" Logic
Since Discord doesn't allow one modal to immediately trigger another without user interaction, the flow will look like this:

Phase A: The Initial Request
User runs /gen.

Modal 1 pops up (Basic Prompt).

User submits.

Phase B: The Enhancement (The "Interim" State)
The bot sends a "Thinking..." message.

The PromptService hits your local LLM endpoint.

The bot sends a message with the enhanced prompt and two buttons: [Generate Now] and [Edit Enhanced Prompt].

Phase C: The Final Polish
If user clicks [Edit Enhanced Prompt], Modal 2 opens with the enhanced text pre-filled.

User hits "Submit," and the job is sent to the ComfyUI Queue.

4. Modular Python Structure (PEP 8)
To keep the code clean, we’ll use a "Provider Pattern" for the LLMs.

Plaintext
src/
├── providers/
│   ├── base.py          # Abstract Base Class for LLMs
│   ├── ollama.py        # Implementation for Ollama API
│   ├── lmstudio.py      # Implementation for LM Studio (OpenAI-compatible)
│   └── unsloth.py       # Implementation for local Unsloth/vLLM
├── services/
│   └── prompt_service.py # Logic for "Enhance -> Edit -> Generate"
5. Local LLM Configuration
Since you mentioned using high-end NVIDIA hardware and local deployments (vLLM/Ollama), the config.py should allow for specific endpoint mapping:

Python
# config.py
LLM_CONFIG = {
    "ollama": {
        "url": "http://localhost:11434/v1",
        "default_model": "starling-lm"
    },
    "lmstudio": {
        "url": "http://192.168.1.50:1234/v1",
        "default_model": "local-model"
    }
}
6. Brainstorming: System Prompts
Since you’re an expert in prompt engineering (specifically Suno/LTX), we can store a library of System Prompt Templates in a prompts.yaml file.

Landscape Template: Focuses on terrain, weather, and lighting.

Portrait Template: Focuses on skin texture, clothing, and bokeh.

Video Template: Focuses on "Match-cuts," "Zhuanchang," and motion vectors.