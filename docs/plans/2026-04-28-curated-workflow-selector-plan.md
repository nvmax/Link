# Curated Workflow Selector Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Create a "Workflow Selector" button that lets users pick from a curated list of workflows in Discord.

**Architecture:** Update the Modal Studio to support a multi-select workflow picker for buttons, and update the bot to display these as a Discord Select Menu.

**Tech Stack:** React (Dashboard), discord.py (Bot), SQLAlchemy (Database)

---

### Task 1: Dashboard UI (Modal Studio)

**Files:**
- Modify: `dashboard/src/components/ModalStudio.tsx`

**Step 1: Add 'selector' to the button type dropdown**
Modify the `<select>` for button type to include `<option value="selector">Workflow Selector</option>`.

**Step 2: Implement the multi-select UI for workflows**
If `btn.type === 'selector'`, show a list of all workflows with checkboxes.

**Step 3: Commit**

---

### Task 2: Bot Result Handler

**Files:**
- Modify: `src/bot/results.py`

**Step 1: Add building logic for the selector button**
In `handle_execution_done`, add a check for `btn_type == "selector"`.

**Step 2: Commit**

---

### Task 3: Discord UI Components (Select Menu)

**Files:**
- Modify: `src/bot/ui.py`

**Step 1: Create ChainSelectView and ChainSelect**
Implement the view that holds the dropdown.

**Step 2: Commit**

---

### Task 4: Interaction Handling

**Files:**
- Modify: `src/bot/views.py`

**Step 1: Handle link_selector interactions**
In `handle_smart_action`, detect the selector button click and show the ephemeral view.

**Step 2: Commit**

---

### Task 5: Verification

**Steps:**
1. Open Dashboard, edit a workflow, add a "Workflow Selector" button.
2. Select 2-3 workflows.
3. Save and Reboot bot.
4. Run a generation in Discord.
5. Click the "Workflow Selector" button.
6. Pick a workflow and verify it starts with the correct prefilled data.
