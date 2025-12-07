# RLCF End-to-End Simulation Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-04
**Status:** ✅ Complete

## Overview

The RLCF End-to-End Simulation is an interactive HTML-based visualization that demonstrates the complete workflow of the Reinforcement Learning from Community Feedback framework. This tool is designed for:

- **Educational purposes** - Understanding how RLCF processes legal tasks
- **Stakeholder presentations** - Demonstrating the system to investors, partners, legal professionals
- **Training** - Onboarding new team members to the RLCF methodology
- **Research** - Analyzing the decision-making process and bias detection algorithms

## Features

### Interactive Step-by-Step Visualization

The simulation walks through 6 key steps of the RLCF pipeline:

1. **Task Creation** - Legal interpretation task submission
2. **Expert Feedback** - Collection of reviews from 5 domain experts
3. **Authority Calculation** - Dynamic authority score computation using the RLCF formula
4. **Aggregation** - Uncertainty-preserving feedback aggregation with Shannon entropy
5. **Bias Detection** - Automated detection of 3 types of bias with mitigation strategies
6. **Final Output** - Synthesized reasoning, recommendations, and traceability

### Real-World Data

The simulation uses a realistic case study:

- **Legal Domain:** Italian civil law (Art. 2043 c.c. - tort liability)
- **Scenario:** Autonomous vehicle accident with pedestrian
- **Experts:** 5 reviewers with varying authority levels (judge, professors, lawyers, researcher, junior)
- **Complexity:** Multidisciplinary (civil law, tech law, AI ethics, automotive)

### Visual Components

- **Timeline Navigation** - Click on any step to jump directly
- **Animated Transitions** - Smooth fade-in effects between steps
- **Interactive Charts** - Chart.js powered visualizations:
  - Authority scores comparison (bar chart)
  - Feedback distribution (doughnut chart)
  - Weighted contribution (pie chart)
  - Bias severity scores (horizontal bar chart)
- **Mathematical Formulas** - Display of RLCF equations with explanations
- **Metrics Cards** - Hover effects on key performance indicators
- **Color-Coded Status** - Green (approved), yellow (needs revision), red (rejected)

### Controls

- **Previous/Next Buttons** - Manual step navigation
- **Auto Play Mode** - Automatic progression through steps (5 seconds per step)
- **Reset Button** - Return to the beginning
- **Timeline Dots** - Visual progress indicator with clickable navigation

## Usage

### Running the Simulation

#### Option 1: Direct File Opening (Recommended)

Simply open the `simulation.html` file in any modern web browser:

```bash
# From the project root
open simulation.html  # macOS
xdg-open simulation.html  # Linux
start simulation.html  # Windows
```

#### Option 2: HTTP Server

For better performance with large files, run a local HTTP server:

```bash
# Using Python 3
cd /path/to/MERL-T_alpha
python3 -m http.server 8888

# Then open in browser:
# http://localhost:8888/simulation.html
```

#### Option 3: Docker Container

If you prefer a containerized environment:

```bash
docker run -d -p 8080:80 -v $(pwd):/usr/share/nginx/html:ro nginx:alpine

# Access at:
# http://localhost:8080/simulation.html
```

### Navigation Tips

1. **Sequential Learning:** For first-time users, start from Step 1 and proceed sequentially using the "Next" button
2. **Quick Reference:** Use timeline dots to jump directly to specific steps
3. **Auto Play Mode:** Enable auto-play for demonstrations or presentations (5s per step)
4. **Hover for Details:** Hover over expert cards and metrics for subtle animations
5. **Read Carefully:** Each step includes detailed explanations, formulas, and insights boxes

### Educational Workflow

#### For Stakeholders (15 minutes)

1. Start at Step 1 - Show the legal case scenario
2. Jump to Step 3 - Explain authority scoring formula
3. Move to Step 5 - Demonstrate bias detection capabilities
4. End at Step 6 - Review final output with traceability

#### For Technical Team (30 minutes)

1. Go through all 6 steps sequentially
2. At Step 3, pause to discuss the authority formula: `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`
3. At Step 4, analyze the Shannon entropy calculation for disagreement
4. At Step 5, review the bias detection algorithms and code snippets
5. At Step 6, examine EU AI Act compliance features

#### For Legal Professionals (20 minutes)

1. Step 1: Focus on the task structure and legal domain
2. Step 2: Review the diverse expert credentials and reasoning
3. Step 4: Understand how consensus is calculated
4. Step 6: Examine key legal principles, recommendations, and uncertainty flags

## Technical Details

### Dependencies

The simulation is a **standalone HTML file** with no installation required. It uses CDN-hosted libraries:

- **Tailwind CSS 3.x** - Utility-first CSS framework
- **Chart.js 4.4.0** - Interactive charts
- **GSAP 3.12.2** - Animation library

All dependencies are loaded from CDNs, ensuring the simulation works offline-first after the initial load.

### Browser Compatibility

- ✅ Chrome 90+ (recommended)
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ⚠️ Internet Explorer: Not supported (use modern browsers)

### Performance

- **File Size:** ~71 KB
- **Load Time:** <2 seconds on average connection
- **Memory Usage:** ~50 MB (including Chart.js canvases)
- **Recommended Screen:** 1280x720 or higher

### Customization

To customize the simulation data, edit the `simulationData` object in the `<script>` section:

```javascript
const simulationData = {
    task: { /* Your task data */ },
    experts: [ /* Your expert profiles */ ],
    aggregation: { /* Aggregation metrics */ },
    bias: { /* Bias detection results */ },
    output: { /* Final output */ }
};
```

#### Example: Adding a New Expert

```javascript
{
    id: 6,
    username: "prof_nuovi_tech_ethics",
    credentials: "Professor of Technology Ethics - Politecnico di Milano, 12 years",
    baselineScore: 0.80,
    trackRecord: 0.85,
    performance: 0.82,
    authorityScore: 0.823,
    feedback: "APPROVED",
    reasoning: "Your reasoning here...",
    confidence: 0.90,
    expertise_areas: ["Tech Ethics", "AI Governance"]
}
```

#### Example: Modifying Authority Weights

To change the RLCF formula weights (α, β, γ), update the formula display and recalculate authority scores:

```javascript
// Default: α=0.3, β=0.4, γ=0.3
// New weights: α=0.2, β=0.5, γ=0.3
const alpha = 0.2, beta = 0.5, gamma = 0.3;

expert.authorityScore = alpha * expert.baselineScore +
                        beta * expert.trackRecord +
                        gamma * expert.performance;
```

## Use Cases

### 1. Investor Presentations

**Scenario:** Demonstrating RLCF's unique value proposition to potential investors.

**Approach:**
- Use auto-play mode for continuous flow
- Focus on Step 5 (Bias Detection) to show AI safety features
- Highlight EU AI Act compliance in Step 6
- Emphasize the mathematical rigor in Step 3

### 2. Academic Conferences

**Scenario:** Presenting RLCF research at NeurIPS, ICML, or legal tech conferences.

**Approach:**
- Deep dive into Step 3 (Authority formula)
- Analyze Step 4 (Aggregation algorithms, Shannon entropy)
- Discuss Step 5 (Bias detection methodology)
- Provide simulation link in paper supplementary materials

### 3. Legal Firm Training

**Scenario:** Training lawyers on how RLCF assists with legal research.

**Approach:**
- Step 1: Explain task types and legal domains
- Step 2: Show how expert feedback is collected
- Step 6: Focus on actionable recommendations and uncertainty flags
- Emphasize human-in-the-loop oversight

### 4. Regulatory Compliance Audits

**Scenario:** Demonstrating AI transparency to regulators (e.g., EU AI Act auditors).

**Approach:**
- Step 6: Show full traceability with Trace IDs
- Step 5: Demonstrate proactive bias detection
- Step 4: Explain uncertainty quantification
- Provide technical documentation links

### 5. Developer Onboarding

**Scenario:** New team members learning the RLCF codebase.

**Approach:**
- Map simulation steps to actual code modules:
  - Step 1 → `merlt/rlcf_framework/models.py` (Task model)
  - Step 2 → `merlt/rlcf_framework/models.py` (Feedback model)
  - Step 3 → `merlt/rlcf_framework/authority_module.py`
  - Step 4 → `merlt/rlcf_framework/aggregation_engine.py`
  - Step 5 → `merlt/rlcf_framework/bias_analysis.py`
- Use simulation as a reference while reading code

## Extending the Simulation

### Adding New Steps

To add a new step (e.g., "Knowledge Graph Enrichment"):

1. Add a new step object to the `steps` array:

```javascript
{
    title: "🔗 Step 7: Knowledge Graph Enrichment",
    render: () => `
        <div class="step-card active bg-white/10 backdrop-blur-lg rounded-2xl p-8">
            <h2 class="text-3xl font-bold text-white mb-6">Your Title</h2>
            <!-- Your HTML content -->
        </div>
    `
}
```

2. Update the timeline navigation to include the new dot

3. Adjust the progress calculation in `updateTimeline()`

### Adding New Charts

To add a custom Chart.js visualization:

1. Add a `<canvas>` element in your step's HTML:

```html
<canvas id="myCustomChart"></canvas>
```

2. Create a rendering function:

```javascript
function renderMyCustomChart() {
    const ctx = document.getElementById('myCustomChart');
    if (!ctx) return;

    if (charts.myCustom) charts.myCustom.destroy();

    charts.myCustom = new Chart(ctx, {
        type: 'line', // or 'bar', 'doughnut', 'radar', etc.
        data: { /* Your data */ },
        options: { /* Your options */ }
    });
}
```

3. Call it in your step's render function with `setTimeout`:

```javascript
render: () => {
    setTimeout(() => {
        renderMyCustomChart();
    }, 100);
    return `<!-- Your HTML -->`;
}
```

### Theming

To change the color scheme, modify the Tailwind classes:

**Current Theme:** Purple gradient background with green accents

**Dark Blue Theme Example:**

```html
<!-- Change in <body> tag -->
<body class="p-8" style="background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);">

<!-- Change accent colors -->
<!-- From: bg-green-500, text-green-400 -->
<!-- To: bg-blue-500, text-blue-400 -->
```

## Integration with Backend

The simulation currently uses hardcoded data. To connect it to the live RLCF backend:

### Option 1: Fetch from API

Replace `simulationData` with an API call:

```javascript
async function loadSimulationData(taskId) {
    const response = await fetch(`http://localhost:8000/tasks/${taskId}/simulation-data`);
    const data = await response.json();
    return data;
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    simulationData = await loadSimulationData(42);
    renderStep();
    updateTimeline();
});
```

### Option 2: Embed in React App

Convert the simulation to a React component:

```jsx
// frontend/rlcf-web/src/components/Simulation.tsx
import React, { useState, useEffect } from 'react';
import { Chart } from 'chart.js';

export const RLCFSimulation: React.FC<{ taskId: number }> = ({ taskId }) => {
    const [data, setData] = useState(null);

    useEffect(() => {
        fetch(`/api/tasks/${taskId}/simulation-data`)
            .then(res => res.json())
            .then(setData);
    }, [taskId]);

    // Render simulation steps
    return (/* JSX version of HTML */);
};
```

### Option 3: Server-Side Rendering

Generate the HTML dynamically with Jinja2 templates:

```python
# merlt/rlcf_framework/main.py
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

@app.get("/simulation/{task_id}", response_class=HTMLResponse)
async def render_simulation(task_id: int, request: Request):
    task = await get_task_with_feedback(task_id)
    simulation_data = build_simulation_data(task)
    return templates.TemplateResponse("simulation.html", {
        "request": request,
        "data": simulation_data
    })
```

## Troubleshooting

### Charts Not Rendering

**Symptom:** White/empty boxes where charts should be

**Solutions:**
1. Check browser console for Chart.js errors
2. Ensure internet connection (CDN loads)
3. Try refreshing the page
4. Check if `setTimeout` delay is sufficient (increase from 100ms to 500ms)

### Animations Not Smooth

**Symptom:** Jerky transitions between steps

**Solutions:**
1. Close other browser tabs to free memory
2. Disable browser extensions
3. Use Chrome instead of Firefox for better GSAP performance
4. Reduce canvas resolution in Chart.js options

### Content Overflow

**Symptom:** Text or elements cut off on small screens

**Solutions:**
1. Use horizontal scrolling: Add `overflow-x: auto` to containers
2. Adjust font sizes for mobile: Use `@media` queries
3. Increase minimum width: `min-width: 1280px` on main container

### Timeline Not Updating

**Symptom:** Progress bar stuck or dots not changing color

**Solutions:**
1. Check `updateTimeline()` is called after `renderStep()`
2. Verify `currentStep` variable is updating
3. Inspect `timeline${i}` element IDs match the HTML

## Best Practices

### For Presentations

1. **Test beforehand** - Open the simulation 10 minutes before presenting
2. **Use presenter mode** - Full-screen browser window
3. **Prepare talking points** - 2-3 key insights per step
4. **Have backup** - Export to PDF (print to PDF in browser) as fallback
5. **Practice transitions** - Know when to click Next vs use Auto Play

### For Documentation

1. **Link in README** - Add prominent link to simulation in project README
2. **Include in onboarding** - Make it part of new hire checklist
3. **Version control** - Tag simulation releases with git tags
4. **Screenshots** - Capture key steps for documentation
5. **Feedback loop** - Collect user feedback for improvements

### For Development

1. **Keep data realistic** - Use real legal cases (anonymized)
2. **Update regularly** - Sync with backend model changes
3. **Test cross-browser** - Verify on Chrome, Firefox, Safari
4. **Optimize performance** - Use lazy loading for heavy components
5. **Document changes** - Update this guide when adding features

## Metrics & Analytics (Future)

To track simulation usage, consider adding:

```javascript
// Google Analytics 4
gtag('event', 'simulation_step_view', {
    'step_number': currentStep,
    'step_title': steps[currentStep].title
});

// Custom backend logging
fetch('/api/analytics/simulation', {
    method: 'POST',
    body: JSON.stringify({
        event: 'step_view',
        step: currentStep,
        timestamp: new Date().toISOString()
    })
});
```

## Resources

### Related Documentation

- [RLCF Core Paper](../RLCF.md) - Theoretical foundations
- [Authority Module](../../technical/architecture.md#authority-scoring) - Authority formula details
- [Aggregation Engine](../../technical/architecture.md#aggregation) - Uncertainty preservation
- [Bias Analysis](../../technical/architecture.md#bias-detection) - Bias detection algorithms
- [Quick Start Guide](./quick-start.md) - Getting started with RLCF

### Code References

- **Authority Calculation:** `merlt/rlcf_framework/authority_module.py:15-45`
- **Feedback Aggregation:** `merlt/rlcf_framework/aggregation_engine.py:78-120`
- **Bias Detection:** `merlt/rlcf_framework/bias_analysis.py:30-90`
- **Task Model:** `merlt/rlcf_framework/models.py:50-85`

### External Libraries

- [Chart.js Documentation](https://www.chartjs.org/docs/latest/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [GSAP Animation](https://greensock.com/docs/)

## Contributing

To improve the simulation:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/simulation-enhancement`
3. Edit `simulation.html`
4. Test thoroughly across browsers
5. Update this guide with your changes
6. Submit a pull request with screenshots

## License

This simulation is part of the MERL-T project, licensed under the same terms as the main project.

---

**Questions or Issues?** Open an issue on GitHub or contact the ALIS team.

**Version History:**
- **1.0.0** (2025-11-04): Initial release with 6-step visualization
