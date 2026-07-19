# 🎨 Discord Activity Interactive Inpainting Setup Guide

LINK includes built-in support for Discord Activities powered by the **Discord Embedded App SDK**. This allows users to open an interactive image painting tool directly inside Discord's iframe to draw masks for inpainting without leaving Discord.

---

## 1. Discord Developer Portal Setup

To enable Discord Activities for your bot:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Select your application / bot.
3. Click **Activities** in the left sidebar menu.
4. Toggle **Enable Activities** to **ON**.
5. Under **URL Mappings**, add the following mappings:

   | Prefix | Target |
   |---|---|
   | `/` | `yoursite.com` |
   | `/api` | `yoursite.com` |

   *(Replace `yoursite.com` with your actual domain or tunnel hostname)*

   > [!NOTE]
   > Do **NOT** include `https://` in the Target field — Discord automatically adds the HTTPS protocol.

6. Under **OAuth2 → General**:
   - Copy your **Client ID** and save it in your `.env` file as `DISCORD_CLIENT_ID`.

7. Under **Installation**:
   - Ensure your bot has the following OAuth2 scopes enabled:
     - `bot`
     - `applications.commands`
     - `activities.read`
     - `activities.write`

---

## 2. Network & Server Setup

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
DISCORD_CLIENT_ID=your_application_client_id
INPAINT_SERVER_DOMAIN=aidigitalcreations.com
INPAINT_SERVER_PORT=8000
```

- `DISCORD_CLIENT_ID`: Your Discord application ID from the Developer Portal.
- `INPAINT_SERVER_DOMAIN`: The domain registered in your URL Mappings.
- `INPAINT_SERVER_PORT`: Port where the inpaint server listens locally (default `8000`).

---

## 4. Dashboard Configuration

In the LINK Dashboard under **Mission Control**:
- You can manage `DISCORD_CLIENT_ID`, `INPAINT_SERVER_DOMAIN`, and `INPAINT_SERVER_PORT`.
- Click **Copy Dev Portal Settings** to quickly copy the exact URL Mappings to your clipboard.

In the **Visual Architect / List View**:
- Select the `Krea2_Inpaint` workflow (or any workflow using image masking).
- Set the image input type to `inpaint — interactive canvas (Activity)`.

---

## 5. How to Use in Discord

1. In any whitelisted Discord channel, type `/inpaint`.
2. Optionally attach an image to the `/inpaint` command, reply to an existing image message, or run it without an attachment (the bot will pull your most recent generation or prompt for an upload).
3. The bot sends a message with a **🎨 Open Inpaint Studio** button.
4. Click the button — Discord opens the **Inpaint Canvas** inside the embedded iframe.
5. Use the canvas tools:
   - **Brush**: Paint red over areas you want to replace.
   - **Eraser**: Remove mask areas.
   - **Shapes**: Choose between Circle, Square, or Soft (feathered) brush tips.
   - **Size**: Adjust brush diameter slider (5px - 150px).
   - **Opacity**: Adjust the opacity of the brush.   
   - **Undo / Redo / Clear / Mask Toggle**: Full control over mask editing.
6. Type what you want to see in the painted area in the prompt bar (e.g. *"a cute sleeping cat on the sofa"*).
7. Click **🎨 Submit Inpaint**.
8. The canvas automatically closes and the generation runs in Discord using the `Krea2_Inpaint` ComfyUI workflow!
