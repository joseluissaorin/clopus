# AI-First Migration Plan

## Philosophy

**Every regex pattern is a failed opportunity to use intelligence.**

CLOPUS should be a truly universal agent that uses Claude's intelligence for ALL decision-making, not hardcoded patterns.

## Current State vs Target State

### 1. Artifact Inference

**BEFORE (regex):**
```python
# verificator_client.py:325-332
file_patterns = [
    r'create\s+(?:file\s+)?["\']?([a-z0-9_/.-]+\.py)["\']?',
    r'add\s+(?:file\s+)?["\']?([a-z0-9_/.-]+\.py)["\']?',
]
for pattern in file_patterns:
    matches = re.findall(pattern, text)
```

**AFTER (AI-first):**
```python
# Use ai_first.py
from .ai_first import ai_infer_artifacts

artifacts = await ai_infer_artifacts(
    task_title="Implement user authentication",
    task_description="Add JWT-based auth with refresh tokens",
    project_context={"type": "fastapi", "existing_files": [...]}
)
# Returns: ["app/auth/jwt.py", "app/middleware/auth.py", "tests/test_auth.py"]
```

---

### 2. Project Path Detection

**BEFORE (regex):**
```python
# main.py:1040-1051
path_match = re.search(r'(?:Project Path:|Project:)\s*(/workspace/[\w\-]+)', task.description)
if not path_match:
    path_match = re.search(r'/workspace/([\w\-]+)', task.description)
```

**AFTER (AI-first):**
```python
from .ai_first import ai_detect_project

project_path = await ai_detect_project(
    task_title=task.title,
    task_description=task.description,
    available_projects=["nexus-api", "nexus-web", "shared-lib"]
)
# Returns: "/workspace/nexus-api" (based on semantic understanding)
```

---

### 3. Duplicate Detection

**BEFORE (Jaccard similarity):**
```python
# verificator_client.py:428-463
words1 = re.findall(r'\b[a-z]+\b', text1.lower())
words2 = re.findall(r'\b[a-z]+\b', text2.lower())
intersection = len(words1 & words2)
similarity = intersection / union
is_duplicate = similarity > 0.7
```

**AFTER (AI-first):**
```python
from .ai_first import ai_check_duplicate

is_dup, similarity = await ai_check_duplicate(
    "Create User model",
    "SQLAlchemy model for users",
    "Implement User SQLAlchemy model",
    "Database model for user entity"
)
# Returns: (True, 0.95) - Claude understands these are the same
```

---

### 4. Technology Detection

**BEFORE (keyword patterns):**
```python
# objective_parser.py:78-101
tech_patterns = {
    r"\breact\b": "react",
    r"\bfastapi\b": "fastapi",
    r"\bpython\b": "python",
    # ... 20+ patterns
}
for pattern, tech in self.tech_patterns.items():
    if re.search(pattern, text_lower):
        technologies.append(tech)
```

**AFTER (AI-first):**
```python
from .ai_first import get_ai_engine

engine = get_ai_engine()
result = await engine.detect_technologies(
    objective_text="Build a modern web app with real-time features",
    project_files=["package.json", "tsconfig.json"]
)
# Returns: React, TypeScript, WebSocket, Tailwind (inferred from context)
```

---

### 5. Feature Extraction

**BEFORE (bullet point parsing):**
```python
# objective_parser.py:302-303
if re.match(r"^[-*•]\s+", line) or re.match(r"^\d+[.)]\s+", line):
    feature_text = re.sub(r"^[-*•\d.)]+\s*", "", line).strip()
```

**AFTER (AI-first):**
```python
from .ai_first import get_ai_engine

engine = get_ai_engine()
result = await engine.extract_features(
    "Build a todo app with dark mode, user auth, and real-time sync"
)
# Returns structured features with priorities, subfeatures, and implied requirements
```

---

## Integration Steps

### Step 1: Initialize AI Engine in Orchestrator

```python
# orchestrator/main.py

from .ai_first import AIFirstEngine, set_ai_engine

class Orchestrator:
    async def initialize(self):
        # ... existing init ...

        # Initialize AI-First Engine
        self.ai_engine = AIFirstEngine(self.worker_pool, self.memory)
        set_ai_engine(self.ai_engine)
        logger.info("AI-First Engine initialized - regex patterns deprecated")
```

### Step 2: Update verificator_client.py

Replace `_fallback_specify_artifacts` with AI-first:

```python
async def specify_artifacts(self, task_id, title, description, project_path):
    # PRIMARY: AI-first inference
    from .ai_first import ai_infer_artifacts

    artifacts = await ai_infer_artifacts(title, description, {"path": project_path})
    if artifacts:
        return artifacts

    # FALLBACK: Only if AI completely fails
    logger.warning("AI artifact inference failed, using regex fallback")
    return self._regex_fallback_artifacts(title, description)
```

### Step 3: Update heartbeat_agent.py

Replace `_infer_expected_artifacts` regex with AI-first:

```python
async def _infer_expected_artifacts(self, title, description):
    from .ai_first import ai_infer_artifacts

    artifacts = await ai_infer_artifacts(title, description)
    if artifacts:
        return artifacts

    # Fallback to existing regex (deprecated)
    return self._regex_infer_artifacts(title, description)
```

### Step 4: Update main.py project detection

Replace all `re.search(r'/workspace/...')` with AI-first:

```python
async def _get_project_path_for_task(self, task):
    from .ai_first import ai_detect_project

    # Get available projects
    projects = [p.name for p in Path("/workspace").iterdir() if p.is_dir()]

    # AI-first detection
    project = await ai_detect_project(task.title, task.description, projects)
    if project:
        return project

    # Fallback to regex (deprecated)
    return self._regex_detect_project(task)
```

---

## Performance Considerations

### Caching
The AI engine includes a cache to avoid repeated API calls:
- Cache TTL: 5 minutes
- Cache key: hash of (inference_type + prompt)

### Batching
For bulk operations, batch multiple inferences:
```python
# Instead of N separate calls
tasks = [infer_artifacts(t) for t in task_list]
results = await asyncio.gather(*tasks)
```

### Fallback Strategy
Every AI-first function has a regex fallback that's only used when:
1. Worker pool is unavailable
2. API timeout
3. AI returns invalid JSON

---

## Files to Modify

| File | Changes Required |
|------|------------------|
| `orchestrator/main.py` | Initialize AI engine, replace project detection |
| `orchestrator/verificator_client.py` | Replace artifact inference, duplicate detection |
| `orchestrator/heartbeat_agent.py` | Replace artifact inference |
| `orchestrator/objective_parser.py` | Replace tech detection, feature extraction |
| `orchestrator/task_planner.py` | Already migrated to AI-first |
| `orchestrator/skills_engine.py` | Replace skill matching |

---

## Benefits

1. **Universal**: Works for ANY type of project, not just predefined patterns
2. **Context-Aware**: Understands relationships, not just keywords
3. **Self-Improving**: Can learn from past decisions via memory
4. **Semantic**: "Create user model" = "Implement User entity" (regex can't do this)
5. **Extensible**: No need to add new regex patterns for new project types

---

## Example: Before vs After

**Objective**: "Build a real-time collaborative whiteboard with WebRTC"

**BEFORE (Regex)**:
- Project type: "custom" (no pattern matched)
- Technologies: [] (none detected)
- Features: [] (no bullet points found)
- Artifacts: [] (can't infer from title)

**AFTER (AI-First)**:
- Project type: "real-time-web-app"
- Technologies: [React, TypeScript, WebRTC, WebSocket, Canvas API, Redis]
- Features: [
    {name: "Real-time sync", subfeatures: ["cursor sharing", "canvas state sync"]},
    {name: "WebRTC", subfeatures: ["peer connection", "data channels"]},
    {name: "Whiteboard", subfeatures: ["drawing tools", "shapes", "text"]}
  ]
- Artifacts: [
    "src/components/Whiteboard.tsx",
    "src/hooks/useWebRTC.ts",
    "src/services/sync.ts",
    "server/websocket.py"
  ]
