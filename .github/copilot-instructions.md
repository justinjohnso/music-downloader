# GitHub Copilot Instructions

This document provides guidance for GitHub Copilot to generate code and terminal commands that align with this project's standards. These instructions help ensure consistency, readability, security, and maintainability across all contributions.

---

## 🧠 General Philosophy

- Favor **clarity and maintainability** over clever or abstract solutions.
- **Don’t guess** — when Copilot is unsure, it should reference `/explain`, `/terminal`, or `/problems` for clues before continuing.
- Keep logic aligned with the **existing structure and idioms** of the codebase.
- Avoid “magic” or unexplained solutions; strive for transparency in logic.

---

## 🧰 Use Copilot Chat Commands Actively

Copilot should use its tools to write better code. Commands that must be used regularly:

- **/explain** — Before modifying complex or unfamiliar code, explain it.
- **/fix** — Apply only after investigating root cause via terminal and/or Problems tab.
- **/tests** — Generate or update tests when adding/modifying core functionality.
- **/problems** — Review issues in the Problems panel before making assumptions.
- **/terminal** — Check recent output for errors, crashes, or log messages before proposing fixes.
- **/optimize** — Only after baseline functionality is confirmed and tested.

---

## 📁 Project Structure & Layout

Follow consistent structure across projects (backend, frontend, full-stack):

### Backend (Python / Node.js)

- Structure code into `routes/`, `controllers/`, `models/`, `services/`, `utils/`
- Keep `app.py`, `main.py`, or `index.js` minimal — delegate to modules
- Use environment variables (via `dotenv`) — no hardcoded secrets
- Use dependency pinning (`requirements.txt` or `package-lock.json`)

### Frontend (React / JS / TS)

- Use `components/`, `hooks/`, `store/`, `styles/`, `pages/`, `lib/` folders
- Favor functional components and hooks over class components
- Keep logic, UI, and styles cleanly separated

---

## ✨ Code Style & Practices

### Python

- Follow **PEP 8**
- Use `black` for formatting and `flake8` or `pylint` for linting
- Include type hints where useful
- Use docstrings on public classes and functions

### JavaScript / TypeScript

- Use camelCase for vars/functions, PascalCase for components
- Use Prettier and ESLint (Airbnb or Standard config)
- Prefer async/await over callbacks or chained `.then()`
- Use `const` and `let` appropriately (avoid `var`)

---

## 🧪 Testing

- Testing is **not optional** — new logic must include or extend tests
- JS: use `jest` or `vitest` with `.test.js` or `__tests__/`
- Python: use `pytest` with `tests/` folder
- Include:
  - Expected inputs and outputs
  - Edge cases
  - Error handling

---

## ⚙️ Environment & Deployment

- Use `.env` files + `dotenv` for all sensitive config
- Never commit `.env` files or secrets
- Code should work in both local dev and cloud environments (e.g., Vercel, Netlify, Azure)
- Avoid platform-specific logic unless absolutely necessary

---

## 🔐 Security

- Always sanitize and validate user input
- Never expose API keys, secrets, or credentials
- Escape output in templates (JSX, Jinja, etc.)
- Avoid `eval`, `exec`, or any dynamic code execution
- Keep dependencies updated to avoid vulnerabilities

---

## ⚡ Performance & Efficiency

- Don’t optimize prematurely — prefer clarity first
- Use efficient data structures, and avoid redundant computation
- For async operations, always handle errors with try/catch or `.catch()`
- Use pagination or lazy loading for large data sets

---

## 🧹 Clean Code Rules

- Remove unused variables, imports, and commented-out code
- Use descriptive variable and function names
- Group related logic together in modules
- Use comments sparingly — only to explain non-obvious decisions
- **Attribute Sources**: Maintain a `/Documentation/copilot-references.md` file, documenting the origin (tutorials, articles, documentation pages, general concepts) for significant code blocks or techniques generated or adapted by Copilot.

---

## 🖥️ Terminal Command Guidelines

To ensure consistency and efficiency in terminal operations, GitHub Copilot should adhere to the following guidelines when generating or suggesting terminal commands:

- **Package Management**: Prefer `pnpm` over `npm` for package management tasks due to its speed and disk space efficiency. For example, use `pnpm install` instead of `npm install`.

- **Path Specifications**: Use absolute paths when specifying file or directory locations to avoid ambiguity and ensure commands function correctly regardless of the current working directory.

- **Command Verification**: Before executing suggested commands, especially those that modify or delete data, verify their accuracy and impact to prevent unintended consequences.

- **Alias Usage**: Utilize shell aliases to streamline frequent commands and reduce the potential for errors. For example, create an alias for common directory navigation: `alias proj='cd /absolute/path/to/project'`.

- **Environment Consistency**: Ensure that the terminal environment is consistent across development setups by using tools like `.env` files to manage environment variables securely.

- **Documentation and Comments**: When writing shell scripts or complex command sequences, include comments to explain the purpose and functionality of each part, enhancing maintainability and collaboration.

## 📎 Use of Example Code and Repositories

When GitHub Copilot is provided with links to example code (e.g., GitHub repositories, gists, or code snippets from documentation or blog posts), it must:

- **Analyze patterns** and structure from the referenced example before generating new code.
- **Replicate idioms, architecture, and naming conventions** seen in the example when extending or building similar logic.
- **Respect file and folder layouts**, and create new code in harmony with the example's organization.
- Use examples as **primary references** for unfamiliar domains or frameworks.
- Avoid diverging from example patterns unless there's a clear and justifiable improvement.

> 🔗 When given links to `github.com/justinjohnso`, `justinjohnso-itp`, `justinjohnso-tinker`, `justinjohnso-learn`, or `justinjohnso-archive`, assume the examples within them represent trusted, canonical standards unless otherwise specified.

## 📝 Writing Documentation Logs (Blog Format)

When asked to generate a write-up (often referred to as a blog post), GitHub Copilot **must strictly adhere to these guidelines** to generate development logs that authentically replicate the author's specific voice, style, and documentation philosophy. The **non-negotiable primary goal** is meticulous emulation of the author's style as found in the **Reference Examples** below, **not** the creation of generic blog content, formal tutorials, or textbook-like instruction manuals. This requires documenting the development *process* with extreme fidelity, capturing the experience of building or creating something. Think of it as a detailed personal record: "I made this cool thing, here's what the process was like," rather than a guide for others.

### ✅ Voice & Style: Emulate the Author (Mandatory Requirements)

- **Reflective & Factual First-Person Tone**: **MANDATORY**. Consistently use "I," "my," "me." Describe actions *and* the concurrent thought process (e.g., "I decided to use library X because I needed feature Y," "I noticed the output was Z, which made me think the issue was..."). Focus relentlessly on documenting the *exact* sequence of thoughts, actions, trials, errors, and insights *as they occurred in real time*. Honesty about difficulties, dead ends, and moments of confusion is paramount. Write as if documenting your own process for your future self or a close collaborator, capturing the *experience* of the work.
- **Technically Specific but Personal**: **MANDATORY**. Include precise technical artifacts: correctly formatted code snippets, exact error messages, specific commands used, relevant configuration details. Crucially, provide **inline rationale** explaining the *why* behind technical choices, observations, or debugging steps *at the exact moment they are described*. Assume general technical fluency but briefly explain project-specific context only if absolutely necessary for understanding the step described. The goal is to document *your* specific journey, not create a general guide.
- **Direct, Concise, Natural Language**: **MANDATORY**. Write directly and plainly. **Eliminate** filler words, hedging phrases, and unnecessary introductory clauses (e.g., "In order to achieve X, I decided to..."). Use clear, everyday language consistent with the examples. **Actively vary sentence length**; short sentences and single-sentence paragraphs are encouraged for clarity, emphasis, and pacing. Avoid jargon unless it's common in the examples or briefly defined in context. Keep it grounded in your personal experience.
- **Chronological/Logical Process Reporting**: **MANDATORY**. Structure the text **strictly** according to the sequence in which events happened or the logical path taken during troubleshooting or development. **Do not** reorder events for narrative effect or to create a smoother story. The process itself, with all its detours, dictates the structure. This is a log of *what happened*, not a polished tutorial.

### 🧱 Structure Patterns: Follow the Examples (Mandatory Requirements)

- **Context First**: Start **directly** with the specific problem, task, observation, or goal that initiated the work segment being documented. **No generic introductions**.
- **Inline Context & Rationale**: **Integrate** explanations for decisions *within* the description of the action itself. Do not separate 'what was done' from 'why it was done'.
- **Beat-by-Beat Reporting**: Detail **all** significant steps, **especially** including failed attempts, specific debugging actions ("Checked the server logs," "Added a `console.log` here," "Googled the error message 'XYZ'"), moments of confusion ("I wasn't sure why X was happening"), and subsequent corrections or changes in direction. Show the *real*, often non-linear, iterative path.
- **Short, Focused Paragraphs**: Use brief paragraphs, often just 2-4 sentences, centered on a single step, thought, observation, or code block. Use line breaks effectively to visually separate distinct steps or ideas.
- **Abrupt Endings Expected**: End the log **immediately** when the relevant work segment or thought process being documented is complete. **Do not** add concluding summaries, overall reflections, "next steps," or future outlooks unless documenting such a reflection was explicitly part of the final step taken.

### 📌 Stylistic Elements to Replicate (Mandatory Requirements)

- **Specific Technical Details**: **MANDATORY**. Show, don't just tell. Embed correctly formatted code snippets, shell commands, error outputs, relevant configuration snippets, etc., directly into the narrative flow where they occurred.
- **Record of Uncertainty & Iteration**: **MANDATORY**. Explicitly state when unsure ("I wasn't sure how to approach...", "It took several tries to get the syntax right..."), describe the specific debugging process ("The error `ABC` suggested a type mismatch, so I checked the variable declaration..."), and explain how solutions evolved ("Initially, I tried approach X, but it failed because of Y, so I switched to approach Z..."). Capture the non-linear reality of development.
- **Genuine Personal Reactions (Inline & Brief)**: Use **sparingly**, only if authentic to the moment and reflecting the tone in examples. Short, integrated phrases like "That was surprisingly tricky," "Finally got it working!", "I didn't expect that behavior," are acceptable. Keep them concise and part of the flow.
- **Links to Resources (Contextual)**: Include links to documentation, Stack Overflow answers, relevant articles, GitHub issues, etc., *exactly at the point in the narrative* where they were consulted or influenced a decision or understanding.

### 🚫 Patterns to Actively Avoid (Crucial Negative Constraints - Strict Prohibitions)

- **ABSOLUTELY NO Generic Introductions/Conclusions**: **DO NOT** write introductory sentences setting broad context or concluding paragraphs summarizing the work, listing takeaways, or stating future plans. Start with the first concrete action/thought; end with the last documented one.
- **AVOID Overly Optimistic/Promotional Tone**: Report facts, including difficulties, bugs, and failures, neutrally and directly as they happened. **DO NOT** downplay problems, inject artificial positivity, or frame everything as a seamless success.
- **ELIMINATE Hedging/Vagueness**: **Replace** phrases like "it might be," "perhaps," "seems like," "could potentially," "it appears that" with direct statements based on the documented experience ("I observed X," "The result was Y," "The error indicated Z," "I decided to..."). Be specific and factual about *your* process.
- **MINIMIZE Formulaic Transitions**: **Avoid** overuse of "Furthermore," "Moreover," "Additionally," "However," "Thus," "Therefore." Rely on the logical/chronological flow. Use simpler, natural transitions sparingly if needed ("Then," "Next," "So," "Because," "After that").
- **DO NOT Impose Narrative Arcs**: **Resist** structuring the log like a story (setup, conflict, resolution). The factual sequence of technical steps, thoughts, and debugging efforts *is* the required structure.
- **AVOID Writing for a Generic Audience / Instructional Tone**: **DO NOT** explain general programming concepts, common tools, or basic syntax unless the reference examples specifically do so in a similar context. **CRITICAL: DO NOT adopt an instructional or textbook-like tone.** Focus on the specifics of *this particular process* and the decisions *you* made. Assume the reader has the necessary background context or is primarily interested in *your* experience.
- **REJECT Formal/Academic Language**: Use simple, direct language. **Avoid** unnecessarily complex sentence structures or vocabulary not found in the reference examples. Match the natural, sometimes informal, conversational tone seen in the examples.
- **DO NOT Create Polished Narratives**: **Explicitly include** the dead ends, bugs encountered, mistakes made, inefficient paths taken, and moments of confusion. The goal is to document the *real, messy process*, not a sanitized or idealized version.
- **ENSURE Varied Sentence Structure**: **Actively vary** sentence length and beginnings. Avoid long sequences of sentences starting with "I did X. Then I did Y. Next, I did Z." Mix simple and slightly more complex sentences naturally to mimic human writing patterns.

### 🔗 Reference Examples (Canonical Source for Style Emulation)

> ⚠️ Crucially, these examples are the DEFINITIVE GUIDE and the absolute canonical source for the required voice, style, tone, structure, level of detail, and overall documentation philosophy. GitHub Copilot MUST analyze these examples before generating text and continuously refer back to them to ensure alignment. DO NOT DIVERGE from the patterns observed in these examples unless explicitly instructed otherwise for a specific task. The goal is precise emulation.
> 
- [Peter Kallok's promotion letter](https://www.notion.so/Peter-Kallok-s-promotion-letter-0cd6f9e146294528a2913d26a67d813c?pvs=21)
- [APP Essay 1](https://www.notion.so/APP-Essay-1-Final-15a9127f465d8031ab22e7b97424b898?pvs=21)
- [APP Essay 2](https://www.notion.so/APP-Essay-2-Final-1549127f465d8035a301ca09feaafd04?pvs=21)
- [Solfege ML5js](https://www.notion.so/Solfege-ml5-js-1b39127f465d80cf86b3f8b6e824cd1f?pvs=21)
- [A Bitsy Myst game](https://justin-itp.notion.site/A-Bitsy-Myst-game-1ac9127f465d80f2837af5449fa08a92?pvs=4)
- [Designing the controller](https://www.notion.so/Designing-the-controller-pivoting-to-a-different-style-of-game-1a79127f465d80cca95ac7127af780bf?pvs=21)
- [Making a polyrhythm synth](https://www.notion.so/Making-a-polyrhythm-synth-1a59127f465d80fd936cde2974f209c9?pvs=21)
- [Making a hypertext game in Twine](https://justin-itp.notion.site/Making-a-hypertext-game-in-Twine-1a59127f465d809ba7f6c75719ffbf6a?pvs=4)
- [Steampunk Simon game](https://justin-itp.notion.site/Steampunk-Simon-game-1a09127f465d8024a588de52a480e7ef?pvs=4)
- [Building an enclosure for a connected device](https://justin-itp.notion.site/Building-an-enclosure-for-a-connected-device-19e9127f465d80d785a7e1d5231b6b70?pvs=4)
- [Laser cutting](https://www.notion.so/Laser-cutting-1959127f465d80ab85dfec5ae5fa5d52?pvs=21)
- [Data dashboard for Arduino](https://www.notion.so/Data-dashboard-for-a-Wifi-connected-Arduino-1949127f465d80f68c4aec33a6e8ba6d?pvs=21)
- [Spider-Man Platformer Part 1](https://justin-itp.notion.site/Spider-Man-Platformer-Part-1-1929127f465d80dcafafd9871ac1ea82?pvs=4)
- [Just be a rock](https://www.notion.so/Just-be-a-rock-18c9127f465d8071bd50d93e14e22a63?pvs=21)
- [Building my online DJ presence](https://www.notion.so/Final-Building-my-online-DJ-presence-1579127f465d806f9d8ae8ea22ca8a00?pvs=21)
- [Tangible music looper](https://www.notion.so/Midterm-Tangible-music-looper-10e9127f465d8027913dd7522da1378a?pvs=21)
- [Div III Retro](https://dusty-pineapple.notion.site/Div-III-Retro-1d89127f465d808281f3ed600a315398?pvs=21)

---

> Place this file in `.github/copilot-instructions.md` to guide GitHub Copilot's behavior across all repositories.