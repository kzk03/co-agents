# MyVibe Starter Repository

This repository is a starter kit for "vibe coding" with the Gemini CLI. It transforms the development process into a structured, professional workflow, turning your high-level ideas into production-ready code.

## The System Philosophy: A "Digital Agency" in a Box

This system is designed to function like a highly structured, self-contained digital agency within this repository. The core principle is to create a transparent and collaborative workflow between you (the "client" or "director") and the Gemini CLI (the "AI development team"). It's built to take a high-level idea—a "vibe"—and systematically transform it into a well-defined, approved, and correctly implemented piece of software.

The workflow acts as a multi-stage assembly line to ensure quality and alignment at every step:

1.  **Intake (Product Manager):** You provide a creative brief. Gemini's first job is not to code, but to listen and understand, refining your idea into a clear set of requirements.
2.  **Planning & Blueprinting (The "Pre-Production" Phase):** Gemini assembles a "team" of personas (Project Manager, Software Architect, UX Designer, Eng Manager) to create a comprehensive blueprint in `vibedocs/tasks/current_task.md` using a predefined template. This includes architectural alignment, UX design, and a technical implementation plan.
3.  **The Client Checkpoint (Your Approval):** The entire process pauses until you review and approve the blueprint. This is the most important control point, ensuring Gemini never builds the wrong thing and that you are always in control.
4.  **Production (Software Engineer / DevOps Engineer):** Once you approve the plan, Gemini switches to "execution mode," meticulously implementing the blueprint by writing, testing, committing code, and handling deployments.
5.  **Documentation (Technical Writer):** After implementation, a dedicated Technical Writer persona ensures all new features and changes are clearly documented in the `/docs` directory.
6.  **Delivery & Archiving:** When the work is done and validated, the task is formally completed and archived, clearing the way for the next initiative.

## The `vibedocs` Directory: The Project Hub

This is the heart of the workflow. It contains:

*   **`spec.md`:** Your project's high-level specifications, including business goals, features, UX vision, and technical architecture (The "Project Constitution").
*   **`personas.md`:** Descriptions of the AI personas used in the workflow (The "Standard Operating Procedures").
*   **`humans.md`:** A copy of these instructions for your reference (The "Client Onboarding Guide").
*   **`templates/`:** A directory containing templates for different types of tasks (e.g., new features, bug fixes, cloud deployments) to standardize the planning process.
*   **`tasks/current_task.md`:** The active, detailed plan for the current task (The "Statement of Work"). **This is the most important file for you to review.**
*   **`tasks/task_*.md`:** The archive of completed tasks.
*   **`log/log_*.md`:** The daily development logs (The "Audit Trail").

## The `/docs` Directory: Project Documentation

This directory will contain all technical documentation for your project, organized by topic or feature. This ensures that documentation is always up-to-date and easily accessible.

## Getting Started

1.  **Clone this repository.**
2.  **Initialize Your Project Specs** in `vibedocs/spec.md`.
3.  **Make Your First Request** to the Gemini CLI (e.g., "Let's create a simple 'Hello, World!' web server.").
4.  **Review and Approve the Plan** that Gemini presents in `vibedocs/tasks/current_task.md`.
5.  **Watch it Build!**
6.  **Update this README** with your project's specific information.

## Happy Vibe Coding!