# 🌌 Atlas: The Premium Discord-ComfyUI Bridge

Atlas is a high-performance, interactive bridge that transforms your ComfyUI workflows into feature-rich Discord slash commands. It features a real-time Architect Dashboard for workflow manifest management and a sophisticated Discord bot UI.

## ✨ Key Features

- **🚀 Dynamic Slash Commands**: Automatically generates Discord commands from ComfyUI workflows using YAML manifests.
- **🖼️ Native Media Support**: Integrated drag-and-drop slots for Image, Audio, and Video uploads.
- **🧬 Interactive LoRA Picker**: A dedicated ephemeral UI for selecting and managing LoRAs with category sorting.
- **🏗️ Architect Dashboard**: A Next.js-powered visual workspace to map nodes, configure inputs, and design Discord embeds.
- **🔄 Smart Action View**: Regenerate, modify options, or delete generations via a persistent button interface.
- **🎨 Rich UX**: Beautifully formatted embeds with progress bars and real-time status updates.

---

## 🛠️ Installation

### 1. Requirements
- **ComfyUI** (running locally or on a server)
- **Python 3.10+**
- **Node.js** (for the Dashboard)

### 2. Setup
1. Clone the repository and navigate to the project folder.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Dashboard dependencies:
   ```bash
   npm install
   ```
4. Create a `.env` file in the root directory:
   ```env
   DISCORD_TOKEN=
   COMFY_URL=http://127.0.0.1:8188
   DATABASE_URL=sqlite:///data/link.db
   LOG_LEVEL=INFO
   FLUX_MODEL=fluxFusionV24StepsGGUFNF4_V2Fp8.safetensors
   FLUX_STEPS=4
   ALLOWED_GUILD_ID=
   ALLOWED_CHANNEL_ID=

   ```

---

## 🚀 Getting Started

### Start the Bot
```bash
npm run bot
```

### Launch the Architect Dashboard
```bash
npm run dashboard
```
Access the dashboard at `http://localhost:3000` to start mapping your workflows.

---

## 📖 Usage Guide

### Generating Images
Use your dynamic slash commands (e.g., `/kontext`) to start a generation.
- **Drag-and-Drop**: Use the native attachment slots for media.
- **Interactive Fallback**: If you skip a slot, Atlas will "pop up" and request the file before proceeding.

### Managing LoRAs
After the initial command, an ephemeral **LoRA Picker** will appear:
1. Select a **Category** (e.g., "Characters", "Styles").
2. Choose your **LoRA** from the sorted dropdown.
3. Your generation will proceed with the selected injection.

### The Architect Flow
1. Load a workflow in the **Architect Dashboard**.
2. Map ComfyUI nodes to Discord parameters.
3. Design your Discord **Embed** (colors, titles, metadata).
4. Save the manifest to `src/workflows/`.
5. Restart the bot to register the new command instantly.

---

## 📁 Project Structure

- `src/bot/`: Discord bot logic and UI components.
- `src/api/`: ComfyUI interaction and WebSocket handling.
- `src/workflows/`: YAML manifests and LoRA metadata.
- `dashboard/`: Next.js web application for workflow architecting.
- `data/`: Local storage for database and generated assets (ignored by Git).

---

## 🔒 Security
- Always keep your `.env` file private.
- Use `ALLOWED_GUILD_ID` to lock the bot to your private development server.
