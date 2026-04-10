# Design System Document: The Clinical Ethereal

## 1. Overview & Creative North Star
**Creative North Star: "The Clinical Sanctuary"**

This design system moves away from the sterile, rigid, and often anxiety-inducing layouts of traditional medical software. Instead, it embraces a "Clinical Sanctuary" aesthetic—a high-end, editorial approach to healthcare data that feels authoritative yet calming. 

We break the "standard dashboard" template by utilizing **intentional asymmetry** and **tonal depth**. Rather than a flat grid of boxes, the UI is treated as a curated workspace where data breathes. We prioritize high-contrast typography scales (Manrope for headers, Inter for data) to create an information hierarchy that feels less like a spreadsheet and more like a premium medical journal.

---

### 2. Colors & Surface Philosophy
The palette is rooted in medical trust but elevated through sophisticated layering.

*   **Primary (#003D9B / #0052CC):** Use the deeper `primary` for high-authority actions and the `primary_container` for focal points.
*   **Healing Greens (#006B5F / #004F1B):** These are "Success" and "Health" indicators. Use `secondary` for stable metrics and `tertiary` for growth or recovery data.
*   **The "No-Line" Rule:** Sectioning must **never** use 1px solid borders. Boundaries are defined strictly through background shifts. For example, a `surface_container_low` sidebar sitting against a `surface` main content area.
*   **Surface Hierarchy & Nesting:** Treat the UI as physical layers. 
    *   **Level 0 (Base):** `background` (#f7f9fb)
    *   **Level 1 (Sub-sections):** `surface_container_low`
    *   **Level 2 (Active Cards):** `surface_container_lowest` (#ffffff)
*   **The "Glass & Gradient" Rule:** Floating modals or navigation overlays must use **Glassmorphism**. Apply `surface_container_lowest` at 70% opacity with a `24px` backdrop-blur. Main CTAs should utilize a subtle linear gradient from `primary` to `primary_container` to add "soul" and dimension.

---

### 3. Typography: The Editorial Scale
We use a dual-typeface system to balance character with clinical precision.

*   **The Display & Headline (Manrope):** A modern, geometric sans-serif used for top-level summaries and patient names. It provides a human, premium feel. 
    *   *Headline-LG (2rem):* Use for primary dashboard KPIs.
*   **The Interface (Inter):** A workhorse for readability. Use Inter for all data points, labels, and body text. 
    *   *Body-MD (0.875rem):* The standard for patient notes.
    *   *Label-SM (0.6875rem):* Used for metadata, always in `on_surface_variant` to reduce visual noise.
*   **Hierarchy Note:** Always pair a `headline-sm` in `primary` with a `label-md` in `outline` to create an immediate "Question & Answer" visual flow.

---

### 4. Elevation & Depth
In this system, depth is a functional tool, not a decorative one.

*   **Tonal Layering:** Avoid shadows for static content. Place a `surface_container_lowest` card on a `surface_container_low` background to create a "soft lift."
*   **Ambient Shadows:** For active elements (e.g., a dragged chart or a hovered patient file), use a diffused shadow: 
    *   `box-shadow: 0 12px 32px rgba(25, 28, 30, 0.06);` 
    *   The shadow is never black; it is a tinted version of `on_surface`.
*   **The "Ghost Border" Fallback:** When contrast is legally required for accessibility, use `outline_variant` at **20% opacity**. It should be felt, not seen.
*   **Glassmorphism Depth:** Elements that "float" (like a quick-access vitals panel) should use the glass effect to allow the dashboard colors to bleed through, maintaining a sense of place.

---

### 5. Components

*   **Buttons:** 
    *   *Primary:* Gradient fill (`primary` to `primary_container`), `md` (0.75rem) rounded corners.
    *   *Secondary:* `surface_container_high` background with `on_primary_fixed_variant` text. No border.
*   **Cards & Vitals:** **Strictly prohibit divider lines.** Separate medical history items using `8px` of vertical whitespace and a slight background shift on hover. Use `lg` (1rem) corner radius for main cards.
*   **Chips (Status Indicators):** Use `secondary_fixed` for "Stable" and `error_container` for "Critical." Text should always be the corresponding `on_` token.
*   **Input Fields:** Ghost-style inputs. Use `surface_container_highest` as the background with no border. On focus, transition to a `2px` `surface_tint` bottom-border only.
*   **Medical Timelines:** Use a thick 4px `primary_fixed` vertical bar instead of a thin line to denote the passage of time, creating a bold, editorial look.
*   **Specialty Component - The "Vital Bloom":** A glassmorphic circular container for heart rate or SpO2, using a soft glow (`surface_tint` at 10% spread) to indicate active monitoring.

---

### 6. Do’s and Don’ts

**Do:**
*   **Do** use asymmetrical padding (e.g., more padding at the top of a card than the bottom) to create a sense of professional layout.
*   **Do** use `secondary_fixed_dim` for background elements of charts to keep them "soft" and "healing."
*   **Do** use large, high-quality medical iconography with a 1.5pt stroke weight.

**Don't:**
*   **Don't** use 100% black (#000000) for text; always use `on_surface` (#191c1e) to maintain the premium, soft feel.
*   **Don't** use "Drop Shadows" on every card. This creates visual clutter. Stick to Tonal Layering.
*   **Don't** use sharp 90-degree corners. Everything in a healing environment should feel approachable and "softened."
*   **Don't** use standard "Alert Red" for everything. Use `error` (#ba1a1a) sparingly, only for life-critical data.

---
**Director's Closing Note:** 
Remember, we are designing for clinicians who are under high stress. The UI should be a quiet partner. By using background shifts instead of lines and glassmorphism instead of heavy shadows, we create a workspace that feels like a breath of fresh air.