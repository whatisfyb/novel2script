# Pipeline — utility modules used by the multi-service architecture.
#
# Stage-specific implementations live in their respective modules:
#   parser    (Stage 1) — used by services/input_service
#   splitter  (Stage 2) — used by services/input_service, services/structure_service
#   analyzer  (Stage 3) — used by services/structure_service
#   segmenter (Stage 4) — used by services/structure_service
#   assembler (Stage 6) — used by services/orchestrator
#
# Stage 5 (Beat extraction) is implemented in services/beat_service.py
# using a LangGraph Extractor → Critic → Refiner workflow.
#
# Old monolithic pipeline.orchestrator.run_pipeline has been removed;
# orchestration now lives in services/orchestrator.py.
