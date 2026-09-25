"""رصد - اختبارات اختيار المنفذ في نقطة الدخول الوحيدة (run_desktop.py).

الحالة التي تحرسها: برنامج آخر يشغل المنفذ 8000. كان انشغال المنفذ وحده يُفسَّر
«رصد يعمل بالفعل» فيُفتح المتصفح على البرنامج الغريب، أو يفشل الخادم بصمت
فتعرض الواجهة «تعذّر الاتصال بالخادم».
"""
import pytest

import run_desktop


@pytest.fixture
def ports(monkeypatch):
    state = {"busy": set(), "rasad": set()}
    monkeypatch.setattr(run_desktop, "_port_in_use", lambda p: p in state["busy"])
    monkeypatch.setattr(run_desktop, "_is_rasad", lambda p: p in state["rasad"])
    monkeypatch.setattr(run_desktop, "PREFERRED_PORT", 8000)
    return state


def test_free_preferred_port(ports):
    assert run_desktop._choose_port() == (8000, False)


def test_foreign_program_on_8000_moves_to_next_free_port(ports):
    ports["busy"] |= {8000, 8001}
    assert run_desktop._choose_port() == (8002, False)


def test_rasad_already_running_is_reused(ports):
    ports["busy"] |= {8000}
    ports["rasad"] |= {8000}
    assert run_desktop._choose_port() == (8000, True)


def test_gives_up_when_nothing_is_free(ports):
    ports["busy"] |= set(range(8000, 8000 + run_desktop.PORT_TRIES))
    with pytest.raises(SystemExit):
        run_desktop._choose_port()
