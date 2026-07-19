# ☁️ Cloudflare Domain Setup Guide (Direct Domain & SSL Proxy)

This guide walks you through directing a domain you own (e.g., `yourdomain.com`) to your local computer running LINK using **Cloudflare DNS Proxy**. 

Using Cloudflare's proxy gives you **free automatic HTTPS / SSL certificates**, DDoS protection, and masks your actual home IP address from Discord users — without needing to install or manage Cloudflare Tunnels!

---

## 📋 Prerequisites

Before starting, make sure you have:
1. A domain name registered with any registrar (e.g., Cloudflare Registrar, Namecheap, GoDaddy, Google Domains, Porkbun).
2. Access to your home Wi-Fi router's admin panel to set up a port forward.
3. Your PC's local IP address (e.g., `192.168.1.100`).

---

## 🛠️ Step-by-Step Setup

### Step 1: Add Your Domain to Cloudflare

1. Create a free account at [Cloudflare.com](https://dash.cloudflare.com/sign-up).
2. On the Cloudflare Dashboard, click **Add a site**.
3. Enter your root domain (e.g., `yourdomain.com`) and click **Continue**.
4. Select the **Free Plan** and click **Confirm plan**.
5. Cloudflare will scan your existing DNS records. Click **Continue**.

---

### Step 2: Change Nameservers at Your Registrar

Cloudflare will display two assigned nameservers (for example):
- `aria.ns.cloudflare.com`
- `bob.ns.cloudflare.com`

1. Log into the website where you bought your domain (Namecheap, GoDaddy, etc.).
2. Find the **DNS / Nameservers** settings for your domain.
3. Change the nameserver option from *Default* to **Custom DNS / Custom Nameservers**.
4. Paste the two Cloudflare nameservers and save.
5. *Note: Nameserver propagation usually takes 2–15 minutes (up to 24h in rare cases).*

---

### Step 3: Add DNS A Record with Proxy Enabled

1. Find your home public IPv4 address by visiting [whatismyip.com](https://whatismyip.com) or running in terminal:
   ```bash
   curl ifconfig.me
   ```
2. In the Cloudflare Dashboard, go to **DNS → Records**.
3. Click **Add record** and configure:
   - **Type**: `A`
   - **Name**: `@` (points to root domain `yourdomain.com`) or `inpaint` (for subdomain `inpaint.yourdomain.com`)
   - **IPv4 address**: *Your home public IP address*
   - **Proxy status**: **Proxied (Orange Cloud 🧡)**  
     > [!IMPORTANT]
     > The **Orange Cloud Proxy** MUST be enabled. This is what provides automatic HTTPS encryption for Discord Activity iframe compatibility.

4. Click **Save**.

---

### Step 4: Configure Cloudflare SSL/TLS Mode

1. In the Cloudflare sidebar, navigate to **SSL/TLS → Overview**.
2. Set the encryption mode to **Flexible**:
   - **Flexible**: Cloudflare handles HTTPS between Discord users and Cloudflare, and forwards HTTP traffic to your router.

---

### Step 5: Port Forwarding on Your Router

To allow traffic from Cloudflare to reach LINK on your local machine:

1. Open a browser and access your router's gateway (usually `192.168.1.1` or `192.168.0.1`).
2. Locate the **Port Forwarding / Virtual Server** section.
3. Add a new Port Forwarding rule:
   - **Rule Name**: `LINK-Inpaint`
   - **Service / External Port**: `8000` (or your chosen `INPAINT_SERVER_PORT`)
   - **Internal IP**: *Your local PC IP* (e.g., `192.168.1.100`)
   - **Internal Port**: `8000`
   - **Protocol**: `TCP`
4. Save and apply the rule.

#### Windows Firewall Check
Ensure Windows Firewall allows inbound TCP traffic on port `8000`:
- Open **Windows Defender Firewall** → **Advanced Settings** → **Inbound Rules**.
- Create a **New Rule** → **Port** → **TCP** → **8000** → **Allow the connection**.

---

### Step 6: Configure LINK & Discord Developer Portal

#### 1. Update `.env` File
In your LINK root `.env` file, set:

```env
INPAINT_SERVER_DOMAIN=yourdomain.com
INPAINT_SERVER_PORT=8000
```

#### 2. Discord Developer Portal URL Mappings
1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Select your application → **Activities**.
3. Under **URL Mappings**, add:

   | Prefix | Target |
   |---|---|
   | `/` | `yourdomain.com` |
   | `/api` | `yourdomain.com` |

   > [!NOTE]
   > Do **NOT** type `https://` in the Target column. Discord prepends HTTPS automatically.

---

## 🔄 Dealing with Dynamic IP Addresses (Optional)

If your ISP changes your home IP address periodically, you can automatically update your Cloudflare A record using a DDNS script or container:

### Option A: Using `ddns-updater` (Docker)
```yaml
services:
  ddns-updater:
    image: qmcgaw/ddns-updater
    container_name: ddns-updater
    ports:
      - 8000:80000
    volumes:
      - ./data:/updater/data
```

### Option B: Cloudflare DDNS PowerShell / Python Script
You can also run a simple scheduled task that calls Cloudflare's API to update your A record whenever your public IP changes.

---

## 🔍 Troubleshooting

- **Error 522 / 524 (Connection Timed Out)**: Verify that port `8000` is forwarded correctly on your router and Windows Firewall is not blocking inbound TCP traffic on port 8000.
- **SSL / Certificate Errors in Discord**: Make sure Cloudflare **Proxy Status** is set to **Proxied (Orange Cloud)** and SSL mode is set to **Flexible**.
- **Works on PC but not inside Discord**: Verify URL Mappings in the Discord Developer Portal do not include `https://` in the Target box.
