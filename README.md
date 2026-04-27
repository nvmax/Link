# 🔗 LINK: The Ultimate Discord-ComfyUI Bridge

![LINK Banner](./assets/banner.png)


### **Break the barrier.** 

**LINK** is the definitive command center for Generative AI. It’s not just a bridge—it's a professional-grade orchestration suite that elevates ComfyUI into a seamless Discord experience. Architect your workflows, and manage massive model libraries with surgical precision. No manual coding. No compromises. Just pure performance. 

> [!TIP]
> **If you can dream it in Comfy, you can dominate it in Discord.**

---

## 🚀 Core Capabilities

### 🎨 Visual Architect
Turn complex ComfyUI graphs into simple Discord commands.
- **Node-to-Input Mapping**: Visually select which ComfyUI inputs (prompts, seeds, sliders) should be exposed to Discord users.
- **Automatic Type Inference**: LINK intelligently detects if an input is text, a number, or an image upload.
- **Real-time Synchronization**: Changes made in the Architect are instantly reflected in the Discord bot's slash commands.

### 🎭 Modal Studio
Design the perfect user experience for your generation results.
- **Visual Branding**: Customize embed colors, titles, and metadata layouts.
- **Dynamic Action Buttons**: Add custom buttons (Regenerate, Upscale, Video-ify) that trigger chained workflows.
- **Asset Propagation**: Automatically pass generated images or videos from one workflow to the next.

### 📁 LoRA Studio
A professional-grade management system for your model library.
- **Folder-Based Organization**: Group LoRAs into custom categories (Styles, Characters, Poser, etc.).
- **File-First Workflow**: Click "Add LoRA", pick your `.safetensors` file, and LINK handles the rest—extracting names and extensions automatically.
- **Dynamic Prompt Injection**: Automatically append trigger words and apply precise weights to your positive prompts based on your selected LoRA.

---

## 🖼️ Interface Showcase

| Visual Architect | Modal Studio |
| :---: | :---: |
| ![Architect View](./assets/architect.png) | ![Modal Studio](./assets/studio.png) |
| **LoRA Category Folders** | **LoRA Detail Management** |
| ![LoRA Studio Folders](./assets/lora_folders.png) | ![LoRA Detail Management](./assets/lora_details.png) |

---

## 🛠️ Quick Start

> [!IMPORTANT]
> New to LINK? Follow our **[Getting Started Guide](./GETTING_STARTED.md)** for a full step-by-step walkthrough.

### 1. Requirements
- **ComfyUI** running workflows working.
- **Node.js 20+** and **Python 3.10+**.

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/nvmax/Link.git
cd LINK

# Install dependencies
npm install
cd dashboard && npm install && cd ..
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory:
```env
DISCORD_TOKEN=your_token_here
COMFY_URL=http://127.0.0.1:8188
DATABASE_URL=sqlite:///data/link.db
ALLOWED_GUILD_ID=your_server_id
ALLOWED_CHANNEL_ID=your_channel_id
```

### 4. Run the Suite
```bash
# Start the Dashboard & Bot
npm run dev
```

---

---

## 📂 Project Anatomy

> [!NOTE]
> LINK follows a modular architecture where the Dashboard serves as the "Control Plane" and the Bot serves as the "Execution Engine".

- **`src/bot/`**: High-performance Discord integration using `discord.py`.
- **`src/workflows/`**: The brain of the operation—stores your YAML manifests and LoRA registries.
- **`dashboard/`**: A modern Next.js/Tailwind application for visual workflow architecting.
- **`src/api/`**: Robust WebSocket bridge for real-time communication with ComfyUI.

---

## 🤝 Contributing & Community
We love contributions! If you want to help make LINK even better, please check out our **[Contributing Guide](./CONTRIBUTING.md)** for rules and ways to get involved.

---

## 🔒 Security & License
- **Access Control**: Use `ALLOWED_GUILD_ID` to lock your bot to specific servers.
- **Local First**: Your prompts, models, and workflows stay on your hardware. No cloud tracking.
- **License**: LINK is free for **personal, non-commercial use**. For commercial licensing, please see the **[LICENSE](./LICENSE)** or contact [JerrodLinderman@gmail.com](mailto:JerrodLinderman@gmail.com).

---

### ☕ Support the Developer
If you find **LINK** useful and want to help support its continued development, consider buying the dev a coffee!

[![Buy Me A Coffee](https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge&logo=paypal)](https://paypal.me/nvmaxx)

*Built with ❤️ for the ComfyUI Community.*
