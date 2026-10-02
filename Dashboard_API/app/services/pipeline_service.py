import os
import time
from flask import current_app
from full_pipeline import EpiSentinelFullPipeline

class PipelineService:
    _instance = None

    @classmethod
    def initialize(cls, app):
        task1_3_dir = app.config.get("TASK1_3_DIR", "artifacts")
        task2_dir = app.config.get("TASK2_DIR", "artifacts")
        task2_models_dir = app.config.get("TASK2_MODELS_DIR", "models")
        
        # Check if folder exists and is not empty
        if not os.path.exists(task1_3_dir) or not os.listdir(task1_3_dir):
            app.logger.warning(
                f"EpiSentinel model files not found at {task1_3_dir}. Eager loading skipped. "
                "The pipeline will load lazily on the first prediction request."
            )
            return
            
        try:
            app.logger.info("Eagerly loading EpiSentinelFullPipeline...")
            start_time = time.time()
            cls._instance = EpiSentinelFullPipeline(
                task1_3_dir=task1_3_dir,
                task2_dir=task2_dir,
                task2_models_dir=task2_models_dir
            )
            duration = time.time() - start_time
            app.logger.info(f"EpiSentinelFullPipeline loaded successfully in {duration:.2f} seconds.")
        except Exception as e:
            app.logger.error(f"Failed to eagerly load EpiSentinelFullPipeline: {e}")

    @classmethod
    def get_pipeline(cls):
        if cls._instance is None:
            task1_3_dir = current_app.config.get("TASK1_3_DIR", "artifacts")
            task2_dir = current_app.config.get("TASK2_DIR", "artifacts")
            task2_models_dir = current_app.config.get("TASK2_MODELS_DIR", "models")
            
            current_app.logger.info("Lazily loading EpiSentinelFullPipeline...")
            start_time = time.time()
            cls._instance = EpiSentinelFullPipeline(
                task1_3_dir=task1_3_dir,
                task2_dir=task2_dir,
                task2_models_dir=task2_models_dir
            )
            duration = time.time() - start_time
            current_app.logger.info(f"EpiSentinelFullPipeline loaded successfully in {duration:.2f} seconds.")
            
        return cls._instance
