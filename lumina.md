## Lumina: Frictionless Adaptive Learning Platform

**Topic:** An integrated reading solution for real-time text restructuring and cognitive load minimization based on learner proficiency.

### 1. Project Overview

Lumina is a web service designed to eliminate the **"high cognitive entry barriers"** and "context-switching overhead" experienced by English learners when engaging with difficult news articles. By leveraging **Gemini 3 Flash**, Lumina provides proficiency-based text rewriting and multimodal vocabulary acquisition (Dual Coding) to create an optimal **Comprehensible Input ($i+1$)** environment.

**The Meaning of "Lumina"**

> *"Lumina: Illuminating your path to fluent reading."*

- **Clarity:** Derived from the Latin *Lumen* (light), it signifies transforming dense, opaque news text into clear, transparent content tailored to the learner.
- **Invisibility:** Reflecting the philosophy that "Technology should be invisible," it symbolizes an AI that blends seamlessly into the reading flow without friction.
- **Insight:** Beyond mere translation, it uses AI-generated imagery and level-specific restructuring to "engrave" knowledge into the learner's mind.

### 2. Problem Statement

- **Excessively Difficult Input:** Text that far exceeds a learner's level leads to a rapid decline in motivation.
- **Context Switching Overhead:** The flow of reading is broken the moment a learner navigates to a dictionary tab to look up a word.
- **Low Retention:** Traditional methods of simply checking definitions often fail to move information into long-term memory.
- **Complex Corpora:** While learners desire to study "Authentic Corpus" used by native speakers, the lack of difficulty adjustment makes it inaccessible for non-advanced learners.

### 3. Key Features

**Auto-Leveling & Reader View**

- **Adaptive Rewrite:** Real-time adjustment of text difficulty based on a **custom in-app proficiency rubric** (designed by the Lumina team) that feeds a learner-level parameter into the AI prompt.
- **Reading List:** A centralized repository to save and organize news titles and bodies, allowing users to revisit content within the Lumina platform.
- **URL Import:** Users paste any news article URL into Lumina, which crawls the page via Readability.js and instantly delivers a clean, level-adjusted reader view.
- **Distraction-Free Mode:** A "Safari-style" reading interface that strips away intrusive ads and banners during the crawling step.

**Instant Digital Glossing**

- **In-place Glossing:** Instantaneous vocabulary definitions via mouse-over inside the Lumina reader, eliminating the need for tab switching.
- **Three-way Dictionary:** Concurrent provision of English-English (e.g., Longman, Oxford) and English-Korean definitions for multi-faceted understanding.
- **One-Click Save:** A single click on any glossed word adds it to the learner's wordbook without breaking the reading flow.

**Smart Wordbook & AI Corpus**

- **Integrated Vocabulary Management:** Saved words from the reader are organized into a personalized wordbook with review and search functionality.
- **Dual Coding Theory:** Integration of AI-generated images with saved words to store visual and linguistic information simultaneously.
- **Scaffolded DDL:** An AI-filtered corpus that provides authentic example sentences specifically tailored to the learner's proficiency level.

### 4. Pedagogical Rationale

- **Krashen's Input Hypothesis ($i+1$):** Technically automates the delivery of "Comprehensible Input" by mapping the learner's level — assessed through Lumina's own diagnostic rubric — into the rewrite prompt.
- **Cognitive Load Theory:** Maximizes meaningful cognitive resources by removing extraneous elements (ads, tab switching) through the Reader View.
- **Dual Coding Theory:** Enhances memory retention rates by combining textual information with visual AI imagery.
- **Data-Driven Learning (DDL):** Provides the necessary "scaffolding" for corpus interaction, allowing even beginners to study authentic native-speaker usage.

### 5. Technical Implementation

- **LLM Engine:** Gemini 3 Flash (optimized for speed, cost-efficiency, and long-context processing).
- **Backend:** FastAPI (high-speed asynchronous communication for crawl → rewrite → gloss pipelines).
- **Frontend:** Web App (React / Next.js).
- **Data/APIs:** Readability.js (content extraction), Dictionary APIs, DDL Corpus Database.

### 6. Expected Impact

- **Increased Learning Persistence:** Maintains immersion by removing the "friction" of looking up words.
- **Efficient Vocabulary Expansion:** Promotes multi-dimensional acquisition through context and imagery rather than rote memorization.
- **Self-Directed Learning:** Strengthens **Learner Autonomy** by empowering users to choose and consume authentic content suited to their level.
