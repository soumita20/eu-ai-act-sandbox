**Section implemented: Control Outcome Model**
| Question | Interview-ready answer |
|---|---|
| Why separate outcome from applicability and legal timing? | They answer different questions. Applicability describes whether a provision covers the system, temporal applicability describes whether it is effective at the assessment date, and outcome describes what the control execution found. Combining them could turn “not yet effective” into a misleading “not applicable.” |
| Why use a fixed set of outcomes instead of pass or fail? | A binary result cannot represent uncertainty or skipped work honestly. `REVIEW_REQUIRED`, `INSUFFICIENT_EVIDENCE`, and `NOT_EVALUATED` preserve important distinctions for reviewers and downstream policies. |
| Why make the result immutable? | A control result is an assessment record. Preserving it as created helps avoid silently changing earlier findings. A later review or reassessment can be recorded separately. |
| Why does this model not decide legal compliance? | It records a control’s technical result and traceability data. Legal interpretation, aggregation policy, and human review are separate responsibilities. |

**Section implemented: Versioned Control Definition Model**
| Question | Interview-ready answer |
|---|---|
| Why version control definitions separately from evaluator code? | The definition records the legal and assessment contract for a control. Keeping it independent makes changes traceable and lets evaluator implementations evolve without hiding which control version and legal basis produced a finding. |
| Why include both `control_version` and `legal_basis_version`? | The implementation can change without a legal source changing, and legal text can change without the implementation changing at the same time. Recording both helps identify which changed when results differ. |
| Why store assumptions and limitations? | They make the boundaries of a technical check explicit. That helps reviewers interpret findings and avoids presenting a narrow automated check as a complete legal determination. |
| Why use a tuple of evaluation methods? | A control may combine deterministic checks, evidence review, and bounded AI-assisted analysis. Listing the methods keeps that design visible in the catalog. |

**Section implemented: Application profile and assessment intake**
| Question | Interview-ready answer |
|---|---|
| Why separate the application profile from assessment intake? | The profile describes the application version. The intake describes one assessment run, including its legal as-of date. Separating them preserves the profile while allowing reassessments under different dates. |
| Why distinguish `None` from an empty tuple? | `None` means the information was not supplied or is unknown. An empty tuple means the profile owner declared there are no entries. This prevents missing data from being mistaken for a negative answer. |
| Why is personal-data processing a three-state value? | A yes-or-no field would force an unsupported answer when the information is unknown. The explicit `UNKNOWN` state preserves uncertainty for later review. |
| Why require an explicit `as_of_date`? | Legal applicability depends on the date being assessed. Requiring it makes the assessment reproducible and avoids silently using the computer’s current date. |

**Section implemented: Article 2 scope screen**
| Question | Interview-ready answer |
|---|---|
| Why use three fact states? | A missing answer is different from a confirmed “no.” Keeping `UNKNOWN` prevents incomplete profiles from being treated as out of scope. |
| Why not have the function decide scope conclusively? | Article 2 has conditional and activity-specific provisions. The function can screen declared facts and route uncertainty, while qualified review handles nuanced cases. |
| Why keep evidence and rationale for each route? | They make the screening explainable and let a reviewer trace why a route was marked yes, no, or unknown. |
| Why pass the legal-basis version into each assessment? | Scope rules and legal text can change. Recording the version makes later review clear about which text informed the screen. |

**Section implemented: Per-party role assessment**
| Question | Interview-ready answer |
|---|---|
| Why assess roles per party instead of assigning one role to the whole system? | Different parties can have different roles in the same deployment. Provider and deployer roles can also apply to the same party, so one system-wide label would hide relevant distinctions. |
| Why allow a party to have multiple roles? | The definitions describe different activities. A party may develop and place a system on the market, then also use it under its authority. The model records each role independently. |
| Why include `POTENTIAL`, `UNDETERMINED`, and `NOT_ASSESSED`? | They distinguish a possible role, insufficient information, and work that has not been done. None silently becomes a confirmed role. |
| Why track GPAI model-provider status separately? | Providing an AI system and providing a general-purpose AI model are related but distinct questions. Keeping them separate supports the architecture’s separate application and model assessments. |

**Article 5 indicator model added**
Interview practice: Why keep a deterministic indicator screen separate from an LLM? A strong answer is that the screen provides stable identifiers, date handling, evidence links, and predictable routing. An LLM may help surface candidate evidence, but its output should not decide that a legal prohibition applies or override review requirements.
I checked that the two changed Python files parse successfully. I did not add or run tests. The repository folder has no Git metadata, so I could not report a Git diff or status.

**Article 6 indicator added**
Why return separate pathway results instead of one high-risk boolean? Because a system can enter the classification through either Article 6(1) or Article 6(2), and the Annex III pathway has a conditional filter. Keeping them separate preserves which facts triggered the result, where evidence is missing, and which dates apply.

**Article 50 section added**
| Question | Strong answer |
| --- | --- |
| Why separate applicability from whether a notice works? | Applicability depends on the use case and statutory conditions. Notice quality needs separate behavioral checks. Combining them would hide which question the result answers. |
| Why model exceptions separately for each paragraph? | The exception criteria differ. For example, public access to crime reporting affects Article 50(1), while creative works limit the form of deepfake disclosure under Article 50(4). |
| Why keep provider and deployer duties distinct? | The Act assigns different responsibilities to each role. Keeping them separate supports clearer evidence collection and audit trails. |

**GPAI model assessment**
| Code decision | Interview question and answer |
|---|---|
| Separate model-level GPAI status from AI-system classification | **Why separate them?** The Act assigns obligations to both models and systems, but under different provisions and criteria. A GPAI model can be integrated into systems with different intended purposes and risk classifications. |
| Keep threshold presumption distinct from Commission designation | **Does exceeding 10²⁵ FLOPs automatically mean the Commission designated a systemic-risk model?** No. It triggers a presumption of high-impact capabilities and a provider notification process. The model records that as a review indicator, not as a Commission decision. |
| Limit the open-source exception to the obligations named in the Act | **Why not exempt every open-source model from GPAI duties?** The exception is narrow. The copyright policy and public training-content summary remain in scope, and systemic-risk models do not receive the specified relief. |
| Keep evidence references and limitations with the result | **How would you make a compliance screen auditable?** Store the supplied facts, their evidence links, the rule outcome, and the boundaries of the assessment so reviewers can trace and challenge the result. |

**Article 3(1) AI System screen**
| Implementation choice | Interview question and answer |
|---|---|
| Required definition elements are explicit facts | **Why use separate facts instead of one “is AI” field?** It makes the reasoning reviewable. A reviewer can see which element is supported, absent, or unresolved and follow its evidence references. |
| Unknown required facts produce `REVIEW_REQUIRED` | **How does the screen handle uncertainty?** It avoids silently treating missing information as “no.” Unresolved facts stay visible for human review. |
| Adaptiveness is recorded but does not determine the result | **Why is adaptiveness not a required check?** Article 3(1) says an AI system *may* exhibit adaptiveness after deployment, so lack of adaptiveness alone should not exclude it. |
| The result is named a preliminary screen | **Can this output establish that a system is legally an AI system?** No. It is a traceable technical screen against selected definition elements. Legal interpretation and the complete context remain subject to review. |

**GDPR Compliance-Article 5(1)c**
| Code decision | Interview question and answer |
|---|---|
| Assess one processing activity and purpose at a time | **Why make this purpose-specific?** Necessity and relevance depend on the purpose. Reviewing one activity at a time makes the evidence and reasoning traceable. |
| Check adequacy, relevance, and necessity separately | **How does the control represent data minimisation?** It maps the three elements in Article 5(1)(c) to separate facts, so a reviewer can identify which element needs attention. |
| Route unknown facts to review | **Why not treat missing information as compliant?** Missing facts cannot support a reliable finding. The result keeps uncertainty visible for the controller or reviewer. |
| Call the positive result “no gap indicated” | **Does a positive result prove compliance?** No. The assessment relies on declared facts, does not validate them independently, and does not evaluate the other GDPR principles or lawful basis. |

**GDPR Compliance-Article 6(1)**
| Code decision | Interview question and answer |
|---|---|
| Record all six grounds separately | **Why not use a single “lawful basis” field?** Separate claims preserve the controller’s stated rationale and evidence for each ground. |
| Treat a claimed ground as an indicator | **Does recording a ground establish lawfulness?** No. The conditions vary by ground. For example, legitimate interests involves necessity and balancing, while legal obligation and public task require a basis in Union or Member State law. |
| Flag the public-authority restriction on legitimate interests | **Why include this special rule?** Article 6(1)(f) expressly excludes processing by public authorities when they perform their tasks. |
| Require assessment per purpose and activity | **Can an organisation select one basis for every processing operation?** This screen expects review by purpose and activity because the relevant basis depends on the processing context. |

**GDPR Compliance-Article 9**
| Code decision | Interview question and answer |
|---|---|
| Represent the Article 9(1) categories explicitly | **Why list the categories?** It makes the assessment traceable and highlights that biometric data are included here when used for unique identification. |
| Record all ten Article 9(2) grounds as claims | **Does a claimed exception mean processing is permitted?** No. It is a candidate for review. The screen does not verify conditions such as necessity, explicit consent, safeguards, or legal authority. |
| Flag a separate Article 6 assessment | **Is an Article 9 exception enough to process special-category data?** No. The processing also needs an Article 6 lawful basis. |
| Route unknown categories or exception positions to review | **Why not infer the exception from the use case?** The exceptions are conditional and depend on details the screen does not establish. |

**GDPR Compliance-Article 13**

| Code decision | Interview question and answer |
|---|---|
| Distinguish direct collection from other collection sources | **Why check where data came from?** Article 13 covers data collected from the data subject. Data collected elsewhere need a separate Article 14 assessment. |
| Track each information item separately | **Why not record one “privacy notice provided” flag?** Separate items show exactly what is missing or unresolved and support evidence-based review. |
| Record timing and already-known information | **What timing does Article 13 require?** The initial information is generally provided when the personal data are obtained. Article 13(4) says the information duties do not apply where, and insofar as, the person already has the information. |
| Keep notice quality outside this checklist | **Does a complete checklist prove the notice meets Article 12?** No. Clarity, accessibility, and whether the information is understandable still need review. |

**GDPR Compliance-Article 14**
| Code decision | Interview question and answer |
|---|---|
| Route direct collection to Article 13 | **Why separate Articles 13 and 14?** They apply to different collection sources and have different information requirements. |
| Track each applicable delivery deadline | **Why record both the one-month limit and first communication or disclosure?** The first communication or disclosure can set an earlier deadline, so the assessment needs to review each relevant trigger. |
| Record Article 14(5) grounds as claims | **Does a disproportionate-effort claim automatically remove the notice duty?** No. The claim and required safeguards need review, including appropriate measures and making the information publicly available. |
| Keep missing and untimely items visible even when an exception is claimed | **How does the screen support human review?** It shows the claimed exception alongside checklist gaps and safeguard evidence, so reviewers can resolve conflicts instead of hiding them. |

**GDPR Compliance-Article 22**
| Design choice | Interview answer |
|---|---|
| Why use a deterministic screen? | “The scope conditions and listed exceptions are explicit in the regulation, so I represent them as typed facts and deterministic branches. This makes the result reproducible and reviewable.” |
| Why return “candidate review required” instead of “compliant”? | “A claimed exception still needs legal and factual assessment. The tool identifies what to verify without presenting an automated legal conclusion.” |
| Why model special-category data separately? | “Article 22(4) adds conditions when a decision covered by paragraph 2 uses special-category data. Keeping that path explicit makes the additional review requirements visible.” |
| What are the limits of this control? | “It records scope facts and safeguards, but does not decide whether human involvement is meaningful or whether an exception is legally valid. Those require evidence and context.” |

**GDPR Compliance-Article 25**
| Question | Answer to practice |
|---|---|
| Why separate design duties from defaults? | “Article 25 has both a broader duty to integrate safeguards into processing and a specific default duty. Separating them makes the assessment easier to trace to the regulation.” |
| Why capture `UNKNOWN` separately from `NO`? | “Missing evidence is different from evidence of a gap. Keeping those outcomes distinct helps direct review without overstating what the assessment knows.” |
| Does a certification prove Article 25 compliance? | “No. A certification or approved code can contribute evidence, but the assessment still needs to consider the processing context and whether measures are appropriate and effective.” |

**GDPR Compliance-Article 32**
| Question | Answer to practice |
|---|---|
| Why not require encryption and pseudonymisation in every case? | “Article 32 calls for measures appropriate to the risk and says its examples apply as appropriate. The assessment records both the measure’s risk-based appropriateness and its implementation.” |
| Why include regular testing? | “Article 32(1)(d) identifies a process for regularly testing, assessing, and evaluating security measures. Recording that separately makes operational evidence visible.” |
| Does “no gaps indicated” mean the processing is secure? | “No. It means the supplied facts do not identify a gap. A reviewer must still judge the evidence and whether the measures are effective for the specific risk.” |

**GDPR Compliance-Article 33**
| Question | Answer to practice |
|---|---|
| Does the 72-hour deadline apply to processors notifying controllers? | “Article 33(2) says processors notify controllers without undue delay. The 72-hour supervisory authority notification is the controller’s obligation under Article 33(1).” |
| Does every breach need to be reported to the supervisory authority? | “No. A controller does not have to notify when the breach is unlikely to result in a risk to people’s rights and freedoms. The breach still needs to be documented.” |
| Why distinguish missing information from phased information? | “Article 33(4) allows information to be supplied in phases when it cannot all be provided at the same time. That status should prompt follow-up without treating phased delivery itself as a missing item.” |

**GDPR Compliance-Article 34**
| Question | Answer to practice |
|---|---|
| How does Article 34 differ from Article 33? | “Article 33 concerns notification to the supervisory authority, generally when a breach is not unlikely to pose a risk. Article 34 concerns communication to affected individuals when a high risk is likely.” |
| Why is encryption alone not enough to claim the first exception? | “The relevant protection measures must have been applied to the affected data and must render the data unintelligible to unauthorised people. The control checks both conditions.” |
| What does disproportionate effort require? | “It does not remove the need to inform people. Article 34(3)(c) calls for a public communication or similar measure that informs them equally effectively.” |

**GDPR Compliance-Article 35**
| Question | Answer to practice |
|---|---|
| What triggers a DPIA? | “The general trigger is processing likely to result in high risk. Article 35(3) gives specific scenarios, and supervisory authorities also publish lists of processing that require a DPIA.” |
| Why is a positive trigger not a complete legal determination? | “The controller still needs to assess the processing in context. This screen makes potential triggers and missing evidence visible, but does not decide risk or evaluate the DPIA’s quality.” |
| When does Article 36 matter? | “If the DPIA indicates that processing would still be high risk without mitigation, the controller must consult the supervisory authority before processing. This control flags that possibility for separate review.” |

**GDPR Compliance-Article 28 and Article 44-49**
| Question | Answer to practice |
|---|---|
| What does Article 28 require in a processor relationship? | “The controller should use a processor with sufficient guarantees, and the processing needs a binding instrument that covers the required terms and processor obligations. The screen records evidence for those terms, but does not determine whether the contract or actual practices are legally sufficient.” |
| Why is Article 49 treated cautiously? | “Article 49 provides specific derogations, not a general routine transfer mechanism. The screen records the claimed basis and conditions for review instead of treating a selected derogation as automatic approval.” |

**Retrieval source registry**
| Question | Answer to practice |
|---|---|
| Why separate a source from its document version? | “The source identifies where a document comes from. A version records the specific content snapshot used for an assessment. That lets us preserve provenance and reproduce past results.” |
| Why use a content hash in the version ID? | “It gives us a stable way to detect changed content and avoid treating an unchanged re-ingestion as a new legal text version.” |
| Why keep retrieval time separate from publication and effective dates? | “Retrieval time records when we acquired the content. Publication and effective dates describe the document and its legal applicability. They answer different questions.” |

**Document acquisition validation**
1. Why validate before parsing or indexing?
It creates a trust boundary at ingestion. Unsupported, malformed, oversized, or unverifiable content can be rejected before downstream components consume it.
2. Why calculate SHA-256 here?
It gives the content a stable fingerprint. The system can later detect changes, link an indexed document to its exact source version, and reproduce an assessment against the same bytes.
3. Why is the validator not responsible for fetching?
Separating acquisition from validation makes network behavior easier to constrain and audit. A future adapter can own timeouts, redirect policy, and retrieval errors, while this function remains deterministic for a given payload and metadata.
4. What are the limitations of the format checks?
They are intake checks, not full security scanning or format conformance validation. Later parsing should run with resource limits and appropriate isolation, especially for complex formats such as PDF.

**Parsing and Normalization**
1. Why keep the original content hash in parsed output?
It connects every extracted passage to the exact acquired bytes. If the source changes, the new content hash distinguishes that version and supports reproducible assessments.
2. Why preserve page numbers and HTML line numbers?
They give reviewers a path back to the source when checking a citation. Article and paragraph references can also support precise retrieval later.
3. Why use pypdf instead of OCR?
The initial goal is text extraction from text-based regulatory PDFs. OCR adds separate complexity and can introduce recognition errors. Scanned PDFs should be detected and handled as a later, explicit capability.

**Structure-aware chunking**
Why chunk by legal structure instead of fixed character windows?
A fixed window can separate an obligation from its conditions or exceptions. This approach uses parsed sections and article boundaries first, and splits only when a passage exceeds the configured size.
Why include both a chunk ID and a text hash?
The text hash verifies the normalized passage itself. The stable chunk ID combines that hash with source version and position, so the same chunk can be recognized within a versioned source.
What limitation would you call out?
The size limit is measured in characters, not model tokens. The eventual retrieval and embedding stages should validate token limits for the selected embedding model and evaluate whether the chunks retain enough legal context.

**Embedding generation**
Why is the model path local-only?
It prevents inference from depending on a hosted embedding service or silently downloading model files. Model provisioning becomes a separate, explicit setup step.
Why store the model revision and preprocessing version with vectors?
A vector depends on both the model and the text preparation. Recording these values helps identify when vectors need to be rebuilt and supports reproducible index releases.
Why normalize the vectors?
Unit-length vectors support consistent similarity calculations, but the index and retrieval stages still need to use a compatible distance metric and validate retrieval quality.

**Index storage and publication**
The new [index_store.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\retrieval\\index_store.py) provides two publication paths:
- Demo: FileIndexStore writes a deterministic JSON index artifact. It verifies the manifest, record count, source versions, vector dimensions, and content hashes when loading. Publishing the same version is idempotent; a different version cannot silently replace an existing artifact.
- Local and CI: PgVectorIndexStore stores a complete index version and its chunks in one PostgreSQL transaction. The version is marked PUBLISHED only after the stored chunk count is checked. The schema uses pgvector’s vector type and checks each vector’s dimension against its metadata. pgvector documentation
The schema is in [0001_regulatory_index.sql](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\migrations\\0001_regulatory_index.sql). The postgres optional dependency group in [pyproject.toml](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\pyproject.toml) adds Psycopg 3 for the database publisher. I also exported the storage interfaces from [retrieval/__init__.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\retrieval__init__.py).
The publisher validates that every chunk has one matching embedding, checks their hashes, and requires a consistent model configuration and dimension across an index. It derives the index version from the content and embedding configuration, which makes identical publications reproducible.
This implements storage and publication, not search. The migration has not been applied to a database. Full-text and vector query behavior will be the next retrieval section.
The Python files and project manifest parsed successfully. I did not run tests or a database migration.
Interview practice
Why publish an index version atomically?
A reader should only see a complete, validated version. The database transaction prevents partial publication, while the Demo artifact is written as one complete file and then verified when loaded.
Why allow different vector dimensions in the database table?
Embedding models can produce different dimensions. Storing the dimension with each vector lets the schema validate it while preserving older index versions. Search must still filter to a compatible model and dimension.
What is not proven by a successful publication?
That retrieval is relevant or legally sufficient. Publication proves the artifact is structurally consistent and tied to known source versions. Retrieval quality and citation support need separate evaluation.

**Hybrid retrieval**
I added [search.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\retrieval\\search.py) and exported its query and evidence types from [retrieval/__init__.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\retrieval__init__.py). The embedding adapter now also supports embed_query, so it creates query vectors with the same configured model and revision as the indexed chunks.
Both index backends now return the same typed evidence shape:
- Demo: semantic cosine ranking and a lexical BM25-style ranking over the verified packaged index.
- Local and CI: pgvector cosine ranking plus PostgreSQL full-text ranking. The migration includes a GIN index for lexical search. PostgreSQL documents websearch_to_tsquery for user-entered search text, and pgvector provides cosine distance through <=>. PostgreSQL text search, pgvector
The candidate lists are combined with Reciprocal Rank Fusion. Retrieval requires an explicit index version, as_of_date, language, and document-version set. It defaults to binding legal text and official guidance, with optional source and article filters. Unknown effective dates remain eligible, but the citation shows those dates as unknown.
Before returning evidence, the code checks that citations resolve to source and document-version IDs in the index manifest, verifies the passage text hash, and includes source coordinates and embedding metadata. The fused score represents retrieval ranking, not a probability of legal correctness.
Python syntax and project configuration parsed successfully. I did not run retrieval tests or a PostgreSQL query, and the migration has not been applied.
Interview practice
Why use both lexical and semantic retrieval?
Semantic search can find conceptually related text. Lexical search helps with exact identifiers, article numbers, and narrow phrases. Combining the two reduces reliance on either method alone.
Why fuse ranks instead of adding the raw scores?
Cosine similarity and lexical scores are on different scales. Rank fusion combines their ordering without treating those raw scores as directly comparable.
Why require document versions and an as-of date?
Assessments need to use legal text applicable to the stated date. Requiring the version set makes that choice explicit and traceable. The component that resolves legal versions for a date still needs to supply that set.

**Retrieval evaluation milestone**
The evaluation harness and its supporting files are present in the project:
- [evaluation.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\retrieval\\evaluation.py) loads reviewed query sets and calculates retrieval and citation metrics.
- [retrieval-gold-v1.json](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\data\\evaluation-sets\\retrieval-gold-v1.json) is an intentionally empty template. Expected chunk IDs and legal references should only be added after review against the indexed document versions.
- [retrieval-evaluation-v1.schema.json](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\data\\evaluation-sets\\retrieval-evaluation-v1.schema.json) defines the dataset format.
- [retrieval-evaluation.md](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\docs\\retrieval-evaluation.md) explains how to prepare labels and run each backend.
The evaluator accepts a retrieval callback, so it can assess the file and PostgreSQL backends separately without binding the metrics to either one. It records Recall@k, Precision@k, MRR@k, article-reference recall, no-evidence accuracy, and citation validity. The report includes the dataset hash and index version so results can be tied to the exact inputs.
Citation validity checks that returned evidence points to known sources and document versions, belongs to the active index, has source coordinates, and matches its text hash. It does not judge whether the passage supports a legal conclusion. That requires separate human review.
Syntax and data-file parsing checks were completed. I did not run tests.
Interview practice
Why keep the gold set empty for now?
Because expected passages and references must be judged against the exact corpus versions being evaluated. Invented labels would make the metrics look precise without making them reliable.
Why separate retrieval relevance from citation validity?
A result can be relevant but have broken provenance, or have a valid citation that is irrelevant to the question. Those are different failure modes and need separate metrics.
Why record the dataset hash and index version?
They make an evaluation reproducible. If the corpus, labels, or index changes, the recorded identifiers help explain why the metrics changed.
May I proceed to the next section: connecting this retrieval layer to a framework-neutral evidence retrieval service, while keeping LangGraph agents out of scope for now?

**Retrieval service**
I added a shared service and adapters in [service.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\retrieval\\service.py), exported them from [retrieval/__init__.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\retrieval__init__.py), and documented the design in [retrieval-evaluation.md](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\docs\\retrieval-evaluation.md).
The flow is now:
1. The caller builds a validated RetrievalQuery, including the index version, language, as-of date, and document versions.
2. RegulatoryRetrievalService embeds the query.
3. A backend adapter calls either the file-based or PostgreSQL retriever.
4. The service checks that the response is for the requested index version and returns evidence with its citation metadata.
FileRetrievalBackend binds a verified file index to the common backend interface. PgVectorRetrievalBackend wraps the existing PostgreSQL retriever. This keeps application code independent of backend-specific call details, and gives a future API route or LangGraph tool one stable retrieval entry point.
No LangGraph agent was added. The service is designed so an agent can call it later without owning embedding or retrieval policy.
Interview practice
Question	Answer
Why add a service layer when retrievers already exist?	The service coordinates embedding and retrieval behind one interface. Callers do not need to know backend-specific details.
Why use backend adapters?	The file retriever needs a loaded index as an argument, while PostgreSQL uses its connection. Adapters make both fit the same interface without rewriting either retriever.
Why check the index version in the service?	It prevents returning evidence from a different index than the query requested, which protects traceability and reproducibility.
Why keep LangGraph out of this module?	Retrieval is useful to the API, UI, and future workflows. Keeping it framework-neutral avoids coupling core retrieval to one orchestration framework.

**Query construction section**
I added RetrievalRequest, build_retrieval_query(), and RegulatoryRetrievalService.retrieve_request() in [service.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\retrieval\\service.py). They are exported through [retrieval/__init__.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\retrieval__init__.py) and described with a usage example in [retrieval-service.md](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\docs\\retrieval-service.md).
An API or workflow caller can now create a RetrievalRequest and pass it to retrieve_request(). The builder converts it into the existing RetrievalQuery, whose validation runs before embedding and search. The index version, language, as-of date, and document-version IDs remain explicit so callers must identify the legal snapshot they want to search. Source authorities default to binding legal text and official guidance.
Interview practice
Question	Answer
Why add RetrievalRequest instead of exposing RetrievalQuery to every caller?	It gives application code a clear input object and keeps the lower-level search contract behind the service boundary.
Why require document-version IDs and an as-of date?	Retrieval must be scoped to the legal versions that apply. Silently choosing versions could return evidence from the wrong snapshot.
Where does request validation happen?	The builder creates a RetrievalQuery. Its existing validation checks the fields before the service generates an embedding.
Why keep this separate from FastAPI and LangGraph?	Each can translate its own inputs into RetrievalRequest and call the same retrieval service without coupling retrieval logic to either framework.

**FastAPI retrieval endpoint**
The API now exposes POST /api/v1/retrieval/search. The route validates JSON with Pydantic, converts it to the existing RetrievalRequest, and calls the retrieval service. The response schema includes ranked passages and citation provenance. The app factory receives the configured service through dependency injection, keeping model and database setup outside the route.
I also added an optional api dependency group in [pyproject.toml](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\pyproject.toml) and usage notes in [retrieval-api.md](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\docs\\retrieval-api.md). The endpoint follows FastAPI’s documented patterns for Pydantic request bodies and dependency injection.
What each file does
- [retrieval.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\api\\retrieval.py) defines request and response models plus the retrieval route.
- [app.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\api\\app.py) provides create_app(), which mounts the route and accepts a service provider.
- [__init__.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\api__init__.py) exposes the API factory and schemas.
The request requires an index version, an as-of date, and document-version IDs. The route does not decide which legal versions apply. Malformed input and query-contract validation errors return 422 responses. Authentication and authorization are not part of this section, so the route should stay within a trusted development environment until the project security layer is connected.
Interview practice
Question	Answer
Why use Pydantic at the API boundary?	It validates incoming JSON and defines a documented request schema before data reaches retrieval logic.
Why use a dependency provider for the retrieval service?	The route stays independent of model loading and database setup, while the application composition root controls those resources.
Why require an as-of date and document versions?	They make the legal snapshot explicit and reduce the risk of retrieving evidence from an inapplicable version.
Why return citation metadata with each result?	Consumers need provenance to inspect and audit the evidence used by later compliance steps.

**Application composition section**
I added the configured API entry point and its settings:
- [api_settings.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\config\\api_settings.py) reads and validates backend, model, device, index, and database settings from environment variables.
- [bootstrap.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\api\\bootstrap.py) constructs the embedder and selected retrieval backend.
- [main.py](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\src\\eu_ai_act_sandbox\\api\\main.py) exposes the configured FastAPI app for Uvicorn.
- [.env.example](C:\\Applications\\Github Projects\\eu-ai-act-sandbox.env.example) lists the settings. The app does not automatically load a .env file.
- [pyproject.toml](C:\\Applications\\Github Projects\\eu-ai-act-sandbox\\pyproject.toml) now includes an API dependency group and explicit src/ package discovery. Setuptools documents this configuration for source-layout packages. Setuptools package discovery
For the file backend, startup verifies the index and checks that its embedding model ID and revision match configuration. For PostgreSQL, FastAPI provides a fresh service and connection per request, then cleans up the connection through the dependency yield lifecycle. FastAPI dependencies with cleanup
How to explain these choices in an interview
Decision	Interview explanation
Read settings from environment variables	Runtime configuration stays outside source code, so backend, local model path, and database connection can vary by environment.
Require model ID and revision	They must match the published index so query vectors use the same embedding configuration as indexed vectors.
Let auto select the device	The existing embedder can use CUDA when available and fall back to CPU.
Open PostgreSQL connections per request	Each request gets a connection that FastAPI closes after handling, instead of sharing one connection across requests.
Add explicit src/ package discovery	The project can be installed and imported reliably from its src/ layout.


I reviewed the files but did not run the app. There is currently no models folder or default index artifact in the repository, so startup will require a provisioned local model and a published index, or a configured PostgreSQL database. Bind the development server to localhost until authentication and authorization are connected. FastAPI’s Pydantic request models validate the incoming JSON and document the endpoint schema. FastAPI request bodies

**API health-check section.**
- [health.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/health.py) adds GET /health/live and GET /health/ready.
- [app.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/app.py) mounts those routes alongside retrieval.
- [bootstrap.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/bootstrap.py) provides readiness checks for the configured backend.
- [\\_\\_init\\_\\_.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/__init__.py) exports the health API.
- [retrieval-api.md](C:/Applications/Github Projects/eu-ai-act-sandbox/docs/retrieval-api.md) documents the endpoints and their limits.
Code decisions
Liveness only confirms that the process can serve HTTP. It does not check the database, index, or model, so a temporary backend problem does not make the process appear dead.
Readiness checks the local model directory and selected retrieval backend. For PostgreSQL, it uses a three-second connection timeout and verifies that a published index exists. For the file backend, it checks the verified index loaded at startup and confirms its embedding identity matches the configuration.
A failed readiness check returns HTTP 503 with a generic response. Detailed exceptions are logged server-side to avoid exposing database or configuration details. The check does not load model weights or run inference; the model remains lazy-loaded on the first retrieval request.
Interview practice
Question	Strong answer
Why separate liveness and readiness?	Liveness tells an orchestrator whether the process can respond. Readiness tells it whether the service can handle useful requests with its current backend.
Why return a generic 503?	Callers need to know the service is not ready, while internal connection or configuration details belong in protected server logs.
Does readiness prove the model is operational?	No. It confirms the model directory exists. The model loads lazily, so a future enhancement could add an explicit warm-up or inference check if startup cost and GPU memory use are acceptable.

**Observability - structured HTTP request logging**
The API now writes one JSON record per request with a generated request ID, method, route template, status code, and duration. Responses handled by the middleware include that ID in X-Request-ID. Request bodies, query strings, and headers are excluded. Readiness failures log the exception type without exposing internal error details.
The changes are in [app.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/app.py), [logging.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/observability/logging.py), and [health.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/health.py). I documented the behavior in [retrieval-api.md](C:/Applications/Github Projects/eu-ai-act-sandbox/docs/retrieval-api.md).
Code decisions
- JsonLogFormatter emits one JSON object per line, which makes records easier for log collectors to parse.
- configure_logging() configures only the application logger. It does not replace Python’s root logger.
- The request ID is generated by the server, so clients cannot inject arbitrary values into the log.
- The route template is logged instead of the raw URL. This avoids recording query strings or variable path values.
- Metrics and OpenTelemetry exporters are not included in this section.
Interview practice
Question	Suggested answer
Why include a request ID?	It lets an operator correlate a caller’s report with a specific server-side request log.
Why log the route template instead of the full URL?	Templates keep the log useful for grouping requests while avoiding sensitive or high-cardinality URL values.
Why has OpenTelemetry not been added here?	The architecture supports incremental observability. Structured request logs provide a useful first step without introducing exporter configuration before tracing requirements are implemented.

**Request metrics**
Added the request metrics section. The API now exposes GET /metrics in Prometheus exposition format, with a request counter and duration histogram. The implementation is in [metrics.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/observability/metrics.py) and [app.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/app.py). I added prometheus-client to the API optional dependencies in [pyproject.toml](C:/Applications/Github Projects/eu-ai-act-sandbox/pyproject.toml) and documented setup and endpoint behavior in [retrieval-api.md](C:/Applications/Github Projects/eu-ai-act-sandbox/docs/retrieval-api.md).
Code decisions
- A separate Prometheus registry is created for each app instance, avoiding duplicate metric registration if the app factory is used more than once.
- Metrics use normalized methods and route templates, with no raw URLs, queries, request content, or caller identifiers as labels.
- The endpoint is intended for the localhost-bound development API. Protect it before exposing the API on a shared or public network.
- Install the updated API dependencies with uv sync --extra api --extra embeddings.
Interview practice
Question	Suggested answer
Why use route templates as metric labels?	They keep label values bounded. A raw URL could include arbitrary identifiers and create high-cardinality metrics.
Why keep a separate registry per app?	It avoids global registry collisions when creating multiple app instances, such as in separate environments or future tests.
What does the histogram add beyond the request counter?	The counter shows request volume and status distribution. The histogram shows latency distribution, which helps identify slow endpoints.

**FastAPI request tracing with OpenTelemetry**
Added optional FastAPI request tracing with OpenTelemetry.
- [tracing.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/observability/tracing.py) configures tracing and sanitizes request span attributes.
- [app.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/app.py) enables the tracing setup when the optional dependencies are installed.
- [pyproject.toml](C:/Applications/Github Projects/eu-ai-act-sandbox/pyproject.toml) adds separate tracing and otlp extras.
- [retrieval-api.md](C:/Applications/Github Projects/eu-ai-act-sandbox/docs/retrieval-api.md) documents installation and configuration.
OpenTelemetry’s FastAPI instrumentation supports app-level instrumentation and request hooks. Its ASGI instrumentation collects URL and query data, so the hook redacts raw URL, path, query, host, and user-agent values before export. It also disables request and response header capture, including ambient header-capture settings. The templated route remains available for diagnosis. (FastAPI instrumentation guide, ASGI instrumentation source)
Export defaults to none. To print spans locally, install the tracing extra and set OTEL_TRACES_EXPORTER=console. To send spans to an OTLP/HTTP collector, also install the otlp extra and set OTEL_TRACES_EXPORTER=otlp plus OTEL_EXPORTER_OTLP_TRACES_ENDPOINT. The package constraints reflect the current OpenTelemetry releases and FastAPI instrumentation package. (OpenTelemetry exporter configuration, FastAPI instrumentation on PyPI, OpenTelemetry SDK on PyPI)
Interview practice
Question	Suggested answer
Why separate tracing instrumentation from exporters?	The API can create spans without requiring a collector. A deployment chooses whether and where to export them.
Why redact URL fields?	URLs can contain sensitive path values and query parameters. Route templates preserve useful endpoint context without recording those raw values.
Why exclude receive and send spans?	The server request span is enough for this first step. Excluding framework event spans keeps traces smaller and avoids names derived from raw request paths.

**Added a regulatory.retrieval child span around the API call to RegulatoryRetrievalService.retrieve.**
The span records the index version, requested top_k, and number of evidence items returned. It excludes query text, passages, and source identifiers. Service errors propagate through the span context so OpenTelemetry can mark the span as failed. The route passes the configured tracer from [app.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/app.py); the span logic is in [retrieval.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/retrieval.py) and its behavior is documented in [retrieval-api.md](C:/Applications/Github Projects/eu-ai-act-sandbox/docs/retrieval-api.md).
I checked the official OpenTelemetry Python guidance for FastAPI instrumentation and request hooks. I kept the current optional dependency versions aligned with the published OpenTelemetry releases. (FastAPI instrumentation guide, OpenTelemetry instrumentation guide, FastAPI instrumentation package)
Interview practice
Question	Suggested answer
Why create a child span around retrieval?	It separates retrieval latency and failures from the broader HTTP request, making bottlenecks easier to locate.
Why record the index version?	It connects performance and failure observations to the regulatory snapshot used, without recording the user’s query or retrieved evidence.
Why add evidence count after the service returns?	The route can measure the result size without adding evidence contents or source identities to telemetry.

**Added a nested retrieval.query_embedding span around query embedding.**
 It covers lazy model loading and encoding, and records the configured model ID and revision, vector dimensions, and actual execution device. It does not record the query text or vector values.
The optional tracer now passes from the API route through RegulatoryRetrievalService to the embedder. When tracing is disabled, callers keep using the existing no-tracer path. The changes are in [embeddings.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/retrieval/embeddings.py), [service.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/retrieval/service.py), and [retrieval.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/api/retrieval.py). I documented the span in [retrieval-api.md](C:/Applications/Github Projects/eu-ai-act-sandbox/docs/retrieval-api.md).
OpenTelemetry’s Python instrumentation supports explicit nested spans, and the FastAPI integration supports request hooks for sanitizing server-span attributes. (OpenTelemetry instrumentation guide, FastAPI instrumentation guide)
Interview practice
Question	Suggested answer
Why put the embedding span inside retrieval?	It separates model loading and encoding time from backend search time, while preserving the overall retrieval span.
Why include the execution device?	It helps compare latency across CPU and GPU runs without recording user content.
What happens when tracing is unavailable?	The service uses its original embedding call without a tracer, so tracing remains optional.

**The backend search tracing section is implemented.**
A new retrieval.backend_search span measures the file or PostgreSQL search call separately from query embedding. It records a bounded backend label, index version, and evidence count. Query text, passages, and source identifiers are not added to this span.
In [service.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/retrieval/service.py), the service creates the span only when a tracer is provided. nullcontext preserves the ordinary no-tracing path. The service also validates the backend response and index version before recording the evidence count. The tracing behavior is documented in [retrieval-api.md](C:/Applications/Github Projects/eu-ai-act-sandbox/docs/retrieval-api.md).
Implementation decision	Interview explanation
Separate backend span from the embedding span	“A trace can show whether latency comes from model inference or retrieval, which makes performance diagnosis more actionable.”
Use bounded labels: file, postgres, or custom	“Low-cardinality labels support aggregation without creating a new label value for each backend instance.”
Exclude query and evidence content	“Traces are operational telemetry, so I limit recorded data to reduce sensitive-data exposure.”
Validate the response inside the span	“The span’s evidence count is recorded only after the backend returns a valid response for the requested index.”

**Retrievable observability section**
The next retrieval observability section is written: the file and PostgreSQL hybrid retrievers now create separate spans for semantic and lexical search. Each span records the candidate count. The API passes its optional tracer through the built-in retrieval backends; custom backends keep their existing interface.
I updated [search.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/retrieval/search.py), [service.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/retrieval/service.py), and [retrieval-api.md](C:/Applications/Github Projects/eu-ai-act-sandbox/docs/retrieval-api.md).
Code decision	Interview explanation
Separate semantic and lexical spans	“This lets an operator see which retrieval path contributes to search latency.”
Add candidate counts, not content	“The counts help assess search behavior while keeping query and evidence text out of telemetry.”
Use no-op span contexts without a tracer	“Tracing stays optional, so ordinary retrieval does not require OpenTelemetry at runtime.”

**Added retrieval.rank_fusion spans to both the file and PostgreSQL hybrid retrievers.**
They cover reciprocal-rank fusion, citation validation, deduplication, and top-k selection, and record only the final evidence count. I updated the tracing documentation accordingly.
Decision	Interview explanation
Trace fusion separately	“The trace now distinguishes search latency from result assembly and citation checks.”
Record only the result count	“The count helps monitor retrieval behavior without exposing evidence content.”

**retrieve_request now accepts an optional keyword-only tracer**
Also forwards it through the existing retrieval pipeline. Callers can use the application-facing RetrievalRequest API while retaining embedding, backend, semantic, lexical, and rank-fusion spans. I documented that behavior in [retrieval-api.md](C:/Applications/Github Projects/eu-ai-act-sandbox/docs/retrieval-api.md).
Decision	Interview explanation
Make tracing optional	“Callers can enable telemetry without making OpenTelemetry a required runtime dependency.”
Forward the same tracer	“This keeps the whole retrieval operation in one trace across the query-building service boundary.”


**The API route now passes a validated RetrievalRequest**
to service.retrieve_request, which builds the internal query and forwards the tracer. The route span still records the index version, top-k value, and evidence count. I removed the route’s direct build_retrieval_query call.
Decision	Interview explanation
Use retrieve_request at the API boundary	“The route depends on the application-facing request contract instead of constructing the retrieval engine’s internal query.”
Forward the existing tracer	“This preserves one trace across the API, query embedding, backend searches, and rank fusion.”


Verification: In-memory Python syntax compilation passed for the API route and both retrieval modules. I did not run tests.

**Tracing.py**

Added [tracing.py](C:/Applications/Github Projects/eu-ai-act-sandbox/src/eu_ai_act_sandbox/retrieval/tracing.py) and applied its helper to the API, embedding, backend, semantic, lexical, and rank-fusion spans.
Each custom retrieval span now records retrieval.outcome=success or retrieval.outcome=error. Failures set the OpenTelemetry error status and still propagate normally. Automatic exception recording is disabled on these spans, so they do not attach exception messages or tracebacks.
Decision	Interview explanation
Use one helper for all retrieval spans	“A shared tracing policy prevents different retrieval layers from leaking different amounts of exception data.”
Keep a bounded outcome attribute and error status	“Operators can identify failed stages without recording request or evidence content.”
Re-raise the original exception	“Observability does not change the application’s error handling behavior.”