# Usage Scenarios

This file turns the main `supernb` modes into concrete prompts you can use directly.

## 1. Full Product Delivery

Example:

```text
Use supernb to build me a commercial-grade Android expense tracking app in Flutter.
It must support major global languages, especially Southeast Asian languages.
Do not stop at MVP quality.
Use this remote repository: <repo-url>
```

Expected mode:

- `full-product-delivery`
- `product-research-prd`
- `ui-ux-governance`
- `autonomous-delivery`

What `supernb` should do:

- create initiative artifacts
- research competitors and reviews
- write a PRD
- define UI/UX
- implement in batches
- commit continuously

## 2. Brainstorm And Save

Example:

```text
Use supernb to brainstorm an AI travel planner product and save the output locally.
```

Expected mode:

- `brainstorm-and-save`

What `supernb` should do:

- clarify the idea
- explore options
- recommend a direction
- save the result into local markdown artifacts

## 3. UI UX Upgrade For Existing Project

Example:

```text
Use supernb to upgrade the full UI/UX of my local project.
Keep the product intent, but make the interface commercial-grade and fix current readability and contrast issues.
```

Expected mode:

- `ui-ux-upgrade`
- `ui-ux-governance`

What `supernb` should do:

- inspect the project
- define upgrade direction
- implement changes
- run a final design audit

## 4. Implementation Only

Example:

```text
Use supernb to implement the billing module in my current repository.
Plan it, write tests, implement it, verify it, and commit the validated work.
```

Expected mode:

- `implementation-execution`
- `autonomous-delivery`

What `supernb` should do:

- inspect current code
- write a bounded plan
- implement and verify
- commit the result

## Operating Principle

The user may ask for "one shot" output, but `supernb` should still distinguish between:

- full product delivery
- product strategy and documentation only
- UI/UX upgrade only
- implementation only

That split keeps the system usable for both large autonomous runs and focused single-purpose work.

