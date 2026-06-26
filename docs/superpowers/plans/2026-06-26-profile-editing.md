# Profile Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users manually correct AI-parsed candidate Profile fields before using that Profile for search, pipeline, interview, and persisted memory.

**Architecture:** Keep the existing Profile data flow. Add a frontend editor inside `CandidateProfileManager`; edits update the active `CandidateProfile` in `App.tsx`, and saving persists the corrected profile through the existing local profile list and `/api/memory/profile`.

**Tech Stack:** React 19, TypeScript, existing localStorage profile helpers, existing FastAPI memory endpoint.

---

### Task 1: Profile Editing Utilities

**Files:**
- Modify: `frontend/src/lib/profiles.ts`
- Modify: `frontend/src/types.ts`
- Test: `frontend/src/lib/profiles.edit.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/profiles.edit.test.ts` with Node's built-in test runner. The test imports `editableProfileFromUserProfile` and `userProfileFromEditableProfile`, verifies that a parsed profile named `王予` can be corrected to `王予辰`, and verifies comma/newline separated skills and roles become arrays.

- [ ] **Step 2: Run TypeScript check to verify it fails**

Run from `frontend/`: `npx tsc -p tsconfig.app.json --noEmit`
Expected: FAIL because the new helper functions are not exported yet.

- [ ] **Step 3: Write minimal implementation**

Add `EditableProfile` to `frontend/src/types.ts`. Add helper functions in `frontend/src/lib/profiles.ts`:
- `editableProfileFromUserProfile(profile)` returns string fields for name, summary, skills, experiences, education, years_experience, and preferred_roles.
- `userProfileFromEditableProfile(editable, base)` returns a `UserProfile` that preserves unknown base keys and normalizes list fields.

- [ ] **Step 4: Run TypeScript check to verify it passes**

Run from `frontend/`: `npx tsc -p tsconfig.app.json --noEmit`
Expected: PASS.

### Task 2: Profile Editor UI

**Files:**
- Modify: `frontend/src/components/CandidateProfileManager.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `npm --prefix frontend run build`

- [ ] **Step 1: Add update callback plumbing**

Add `onUpdateActiveProfile(profile: UserProfile)` in `App.tsx`. It updates `activeProfile.profile`, refreshes `label` when the old label matched the old display name, preserves id/resumeLabel/preferences/saved, and updates `updatedAt`.

- [ ] **Step 2: Wire callback into profile managers**

Pass `onUpdateActiveProfile` to `CandidateProfileManager` from `PipelineView` and `PreferencesView` call sites. For the `PipelineView` seed-only confirmation profile, editing is disabled unless an actual active profile exists.

- [ ] **Step 3: Add edit mode to active profile card**

Inside `CandidateProfileManager`, add an edit button. In edit mode show inputs for name, summary, skills, preferred roles, years experience, education, and experiences. "套用修改" calls `onUpdateActiveProfile(userProfileFromEditableProfile(...))`; "取消" exits edit mode without changing state.

- [ ] **Step 4: Verify frontend compiles**

Run: `npm --prefix frontend run build`
Expected: TypeScript and Vite build succeed.

### Task 3: Full Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run focused frontend lint/build**

Run: `npm --prefix frontend run lint`
Expected: exit 0.

Run: `npm --prefix frontend run build`
Expected: exit 0.

- [ ] **Step 2: Run backend regression suite**

Run: `python -m ruff check .`
Expected: exit 0.

Run: `pytest -q --basetemp .tmp-pytest-final-release -p no:cacheprovider`
Expected: all tests pass.
