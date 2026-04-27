# 🚀 Getting Started with LINK

Welcome to **LINK**! This guide will walk you through the entire journey—from a raw ComfyUI workflow to a fully functional, interactive Discord command.

---

## 1. Exporting from ComfyUI

To use a workflow in LINK, you must export it in the **API Format**.

1. Open your workflow in **ComfyUI**.
2. Open the **Settings** (gear icon) or ensure **"Enable Dev mode"** is checked in your ComfyUI settings.
3. Click the **"Save (API Format)"** button. This will download a `.json` file.
   - *Note: Standard "Save" JSONs will not work; it must be the API version.*

---

## 2. Importing into LINK

Once you have your `.json` file, it’s time to bring it into the LINK Dashboard.

1. Launch the LINK Dashboard (`npm run dev`) and navigate to the **Architect View**.
2. Click the **"Import Workflow (API)"** button in the sidebar.
3. Select your `.json` file and give it a clean name (e.g., `PortraitGen`).
4. Your workflow will now appear in the sidebar and be ready for architecting.

---

## 3. The Architect View: Mapping for Discord

The Architect View is where you decide what your Discord users can control.

### Using List View
The **List View** breaks your complex ComfyUI graph into individual node cards. This makes it easy to find exactly what you need without hunting through wires.

### Selecting Discord Nodes
On each node card, you will see a list of inputs. 
- Click the **Network/Discord icon** next to an input to "expose" it to Discord.
- Once exposed, that input will become a parameter in your Discord slash command (e.g., `/generate prompt: "A cat"`).

### Understanding the Dropdown Menus
When you expose a node, a dropdown menu appears allowing you to select the **Input Type**:
- **Text - Free text / prompt (modal)**: A standard text box (perfect for prompts) if its a follow up prompt it will display a discord modal window to enter the follow up prompt.
- **Select - Dropdown**: A list of choices (perfect for aspect ratios or models).
- **Image/Video/Audio Upload**: Tells the Discord bot to request a file attachment from the user.

---

## 4. Modal Studio: Designing the Interface

The **Modal Studio** is where you design the "result" message that the bot sends back to Discord.

1. **Branding**: Set your custom Embed Color, Title, and Description.
2. **Layout**: Decide if the generated image should be at the top or bottom of the message.
   - **Note**: Video workflows must have the Image Position: **Top Only!**
3. **Metadata**: Toggle which technical details (like seed or resolution) should be visible to the user.

---

## 5. Custom Buttons & Workflow Chaining

One of LINK's most powerful features is the ability to **Chain Workflows**.

### What is a Custom Button?
Inside the Modal Studio, you can add buttons to your generation result. These aren't just for show—they are interactive triggers.

### Chaining Workflows
1. Click **"Add Button"** in the Modal Studio.
2. Assign it an emoji and a label (e.g., `🎥 Make Video`).
3. Under **Target Workflow**, select another workflow you have already architected.
4. When a user clicks that button in Discord, LINK will automatically take the result of the first workflow and pass it as an input to the second workflow.

*Example: Generate an image with Workflow A -> Click "Make Video" -> Workflow B receives the image and animates it.*

---

## 💡 Pro Tips
- **Keep it Simple**: Only expose the 3-4 most important inputs to Discord to keep the commands user-friendly.
- **Naming Matters**: Give your Discord inputs clear labels (e.g., "Positive Prompt" instead of "input1").
- **Leverage Auto-Detection**: LINK is smart! To help it automatically identify your nodes, use common naming conventions in ComfyUI:
   - **Prompts**: Use nodes like `CLIPTextEncode` or fields named `text`, `prompt`, or `positive`.
   - **Seeds & Steps**: Use `KSampler` nodes or fields named `seed`, `noise_seed`, or `steps`.
   - **Uploads**: Use nodes like `LoadImage`, `LoadVideo`, or `LoadAudio`. The bot also looks for keywords like `img`, `clip`, or `sound` in your field names.
- **Save Often**: Always click **"Save Manifest"** in the header to write your changes to the bot's memory.

---

*Now go build something amazing! If you have questions, join our community or check the [Contributing Guide](./CONTRIBUTING.md).*
