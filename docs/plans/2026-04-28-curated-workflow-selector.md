# Curated Workflow Selector Design

## Overview
This design implements a new Discord button type, "Workflow Selector", which allows users to pick from a curated list of workflows to chain a generation job. This solves the 5-button limit while maintaining control over workflow compatibility.

## Components

### 1. Dashboard (Modal Studio)
- **Button Type**: New `selector` type in `ModalStudio.tsx`.
- **Configuration**: When `type === 'selector'`, show a searchable multi-select list of all available workflows.
- **Manifest Storage**: Store the selected workflows in `btn.target_workflows` (an array of strings).

### 2. Discord Bot (Interactions)
- **Button Generation**: `ResultHandler` builds a button with `custom_id="link_selector_{job_id}"`.
- **Selector Interaction**:
    1. User clicks the button.
    2. Bot looks up the original job and its workflow manifest.
    3. Bot finds the button config and extracts `target_workflows`.
    4. Bot sends an ephemeral message with a `SelectMenu` containing these workflows.
- **Selection Handling**:
    1. User selects a workflow from the dropdown.
    2. Bot triggers `handle_generation_request` for the selected workflow.
    3. Bot pre-fills inputs based on the original job's output assets (using existing `link_chain` logic).

### 3. Data Flow
`Discord Button Click` -> `handle_smart_action` -> `Show Ephemeral Select Menu` -> `Select Menu Callback` -> `New Generation Request`

## Testing Plan
- Verify that the "Add Button" UI in the Dashboard shows the new type.
- Verify that selected workflows are saved to the manifest.
- Verify that clicking the button in Discord shows an ephemeral message with the correct list.
- Verify that selecting a workflow correctly chains the assets (image/video/prompt).
