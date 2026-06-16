# Privacy Policy

**Last Updated:** June 16, 2026

This Privacy Policy explains how **Link** (the "Bot" or "Service") collects, uses, stores, and protects information about you when you interact with our Discord Bot and its associated Web Dashboard (the "Dashboard").

By adding the Bot to your Discord server, interacting with it through commands, or logging into the Dashboard, you agree to the collection and use of information in accordance with this policy.

---

## 1. Information We Collect

To function properly and provide its services, the Bot collects and processes the following types of information:

### A. Data Provided by Discord API
*   **User Information:** Discord User IDs, usernames, are processed and/or cached to authenticate users, manage command access, display queue details, and use user previous generations to regenerate images and video.
*   **Guild (Server) and Channel Information:** Guild IDs, channel IDs, and role IDs are processed to restrict bot commands to designated channels and check admin/moderation permissions.
*   **Message and Command Content:** Text prompts, parameters, and attachments (such as images uploaded for blending or editing) submitted through slash commands (e.g., `/gen`, `/video`, `/merge`) or interactive components are processed to execute generation workflows.

### B. Dashboard Authentication
*   **Discord OAuth2 Data:** When logging into the Dashboard, we use Discord's secure OAuth2 authentication. We request access only to your identity (user ID, username) and guild memberships (to determine which servers you manage). We **never** obtain your Discord password or personal email.

### C. System and Execution Logs
*   Temporary system logs containing transaction status, prompt executions, and error traces are generated to help diagnose technical issues and optimize performance.

---

## 2. How We Use Your Information

We use the collected information solely for the following purposes:
*   **Service Delivery:** To map and run AI image and video generation workflows via the connected ComfyUI instance.
*   **History & Tracking:** To maintain a personal history of your generations on the Dashboard, allowing you to view, retry, or download past generations.
*   **Queue Management:** To manage task priority lanes (e.g., supporters versus standard users) and orchestrate concurrent execution slots.
*   **Improvement & Diagnostics:** To monitor system health, detect bugs, and implement stability improvements.

---

## 3. Data Storage and Retention

*   **Database Persistence:** Basic metadata (such as user IDs, generation parameters, status, and file paths) is stored in our database to support the regeneration features and dashboard functionality.
*   **Asset Storage:** Generated media (images, videos) and uploaded attachments are stored locally, though CDN links in Discord may persist according to Discord's own media policy.
*   **Security:** We employ industry-standard physical, technical, and administrative measures to secure data against unauthorized access, loss, or alteration.

---

## 4. Third-Party Sharing

*   **ComfyUI Backend:** All image/video processing requests are routed to our self-hosted or private ComfyUI API servers. Your prompt inputs and attachments are **not** shared with, sold to, or used to train third-party public AI models.
*   **Discord API:** All interactions, notifications, and generated outputs are sent back through the official Discord API, which is subject to Discord's own Privacy Policy and Terms of Service.
*   **No Commercial Sharing:** We do not sell, rent, or trade your personal information or generation history to advertisers or third-party brokers.

---

## 5. User Rights and Data Deletion

You have full control over your data:
*   **Opt-Out:** You can stop using the Bot at any time, or remove (kick/ban) it from your server.
*   **Data Deletion Requests:** You can request the complete deletion of your generation history and cached profile data by contacting the bot administrator directly or, if available, using the self-service options in the Dashboard.
*   **Inquiries:** For any privacy-related questions or data deletion requests, please contact the Bot Owner/Administrator.

---

## 6. Policy Updates

We may update this Privacy Policy from time to time to reflect changes in our bot features, legal requirements, or Discord's Developer Policy. Significant updates will be accompanied by an announcement in the Bot's support server or within its Discord command feedback.
