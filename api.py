#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from components.report_analysis.data_operations import list_results as analysis_list_results, load_result as analysis_load_result
from utils.inspection_result import list_results, load_result
from fastapi import FastAPI, APIRouter


analysis_router = APIRouter(prefix="/analysis_reports", tags=["analysis"])
inspection_router = APIRouter(prefix="/inspection_reports", tags=["inspection"])

@analysis_router.get("")
def list_analysis_reports():
    return analysis_list_results()

@analysis_router.get("/{id}")
def get_analysis_report(id: str):
    return analysis_load_result(id)

@inspection_router.get("")
def list_inspection_reports():
    return list_results()

@inspection_router.get("/{id}")
def get_inspection_report(id: str):
    return load_result(id)

app = FastAPI(title="KubeEye Report API")
app.include_router(analysis_router)
app.include_router(inspection_router)