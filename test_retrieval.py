from app.retrieval import search_service_knowledge


def test_fault_code_query_returns_source_metadata(seed_db):
    results = search_service_knowledge("E03 温度传感器", limit=3)
    assert results
    assert results[0]["source_name"]
    assert results[0]["source_section"]
    assert results[0]["content"]


def test_unknown_query_returns_empty_or_low_confidence_results(seed_db):
    results = search_service_knowledge("不存在的紫色推进器", limit=3)
    assert all(item["score"] < 0.5 for item in results)


def test_natural_language_fault_description_keeps_relevant_evidence(seed_db):
    results = search_service_knowledge("温度传感器异常", limit=3)

    assert results
    assert results[0]["score"] >= 0.5
    assert results[0]["source_section"]


def test_unrelated_symptom_does_not_create_high_confidence_evidence(seed_db):
    results = search_service_knowledge("现场有异响，但没有故障码", limit=3)

    assert all(item["score"] < 0.5 for item in results)


def test_domain_signal_keeps_temperature_and_offline_evidence(seed_db):
    temperature = search_service_knowledge("连续三次温度告警", limit=3)
    offline = search_service_knowledge("高风险离线告警重复出现", limit=3)

    assert temperature and temperature[0]["score"] >= 0.5
    assert offline and offline[0]["score"] >= 0.5
