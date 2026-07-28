# 🎨 Interactive Inpainting Setup Guide

LINK includes built-in support for interactive image inpainting. This allows users to click a button in Discord to open a dedicated canvas studio in their browser, draw masks, enter prompts, and submit generations directly to ComfyUI.

---

## 1. Network & Server Setup

Your LINK inpaint server **must be reachable via a public HTTPS URL** so Discord users can access the inpaint canvas studio.


Discord Activities load your web application inside an iframe from Discord's `discordsays.com` domain. Therefore, your LINK inpaint server **must be reachable via a public HTTPS URL**.

Choose the setup method that fits your environment:

### Option A: Direct Domain with Cloudflare DNS (Recommended)

If you own a domain (e.g., `yoursite.com`) and manage its DNS via Cloudflare, see our detailed **[Cloudflare Direct Domain Setup Guide](./CLOUDFLARE.md)**.

1. **Cloudflare DNS**:
   - Add an **A record** in Cloudflare pointing your domain/subdomain to your public IP address.
   - Ensure the **Proxy status is set to Proxied (Orange Cloud)**. This automatically provides SSL/HTTPS encryption.

2. **Router Port Forwarding**:
   - On your home/server router, create a port forwarding rule:
     - **External Port**: `8000` (or your chosen `INPAINT_SERVER_PORT`)
     - **Internal IP**: Your local PC IP (e.g. `192.168.1.100`)
     - **Internal Port**: `8000`

3. **Windows Firewall**:
   - Allow inbound TCP traffic on port `8000`.

4. **Start LINK**:
   - LINK binds to `0.0.0.0:8000`. All traffic sent to `https://yoursite.com` will route securely to your local inpaint server. No additional tunnel software is required!

---

### Option B: Cloudflare Tunnel (No domain or CGNAT)

If you don't own a domain, are behind CGNAT, or can't open router ports:

#### Quick Tunnel (Temporary for testing)
```bash
# Download cloudflared from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
cloudflared tunnel --url http://localhost:8000
```
This generates a temporary URL like `https://random-words.trycloudflare.com`. Paste this hostname as your **Target** in the Discord Developer Portal URL Mappings.

#### Persistent Named Tunnel
```bash
# Log in to Cloudflare
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create link-inpaint

# Configure ~/.cloudflared/config.yml
tunnel: <TUNNEL_ID>
credentials-file: ~/.cloudflared/<TUNNEL_ID>.json
ingress:
  - hostname: your-subdomain.your-domain.com
    service: http://localhost:8000
  - service: http_status:404

# Route DNS and run
cloudflared tunnel route dns link-inpaint your-subdomain.your-domain.com
cloudflared tunnel run link-inpaint
```

---

## 3. Environment Configuration (`.env`)

Add the following to your root `.env` file:

```env
INPAINT_SERVER_DOMAIN=aidigitalcreations.com
INPAINT_SERVER_PORT=8000
```

- `INPAINT_SERVER_DOMAIN`: The domain registered in your URL Mappings.
- `INPAINT_SERVER_PORT`: Port where the inpaint server listens locally (default `8000`).
- *(Optional)* `DISCORD_CLIENT_ID`: Your Discord application ID. **LINK automatically retrieves this from your running bot instance**, so configuring this manually is optional.

---

## 4. Dashboard Configuration

In the LINK Dashboard under **Mission Control**:
- You can manage `INPAINT_SERVER_DOMAIN` and `INPAINT_SERVER_PORT`.
- Click **Copy Dev Portal Settings** to quickly copy the exact URL Mappings to your clipboard.


In the **Visual Architect / List View**:
- Select the `Krea2_Inpaint` workflow (or any workflow using image masking).
- Set the image input type to `inpaint — interactive canvas (Activity)`.

---

## 5. How to Use in Discord

1. In any whitelisted Discord channel, type `/inpaint`.
2. Optionally attach an image to the `/inpaint` command, reply to an existing image message, or run it without an attachment (the bot will pull your most recent generation or prompt for an upload).
3. The bot sends a message with the **🎨 Open Inpaint Studio** button.
4. Click **🎨 Open Inpaint Studio** — the **Inpaint Canvas** opens in your browser window or in-app overlay.
5. Use the canvas tools:
   - **Brush**: Paint red over areas you want to replace.
   - **Eraser**: Remove mask areas.
   - **Lasso Tool**: Draw freehand polygon shapes to select custom geometric mask areas.
   - **Magic Wand (Content-Aware Region Fill)**: Click contiguous color regions with adjustable **Wand Tolerance** to auto-mask matching color areas.
   - **Grid Selection Overlay & Section Fill**: Overlay grids (1/2, 1/3, 1/4, 3 Horizontal, 3 Vertical, etc.) and click any grid section to instantly fill or erase that cell.
   - **Zoom & Pan Controls**: Zoom from 25% to 500% via UI controls or mouse wheel; use the Pan tool to drag around the canvas viewport.
   - **Shapes & Sliders**: Choose Circle, Square, or Soft feathered tips; adjust brush size, wand tolerance, opacity, and overlay visibility.
   - **Undo / Redo / Clear / Mask Toggle**: Full control over mask history and editing.
6. Type what you want to see in the painted area in the prompt bar (e.g. *"a cute sleeping cat on the sofa"*).
7. Click **🎨 Submit Inpaint**.
8. The canvas automatically closes the window upon completion, and the generation runs asynchronously using your configured ComfyUI inpainting workflow!




