#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

# --- настройки ------------------------------------------------------------
BASE_URL = "http://192.168.1.139"
# Если непустой — используется как Bearer (например из окружения: ACCESS_TOKEN=…).
ACCESS_TOKEN = ""

POLL_INTERVAL_SEC = 1.0
POLL_DEADLINE_PER_TASK_SEC = 300.0
# --------------------------------------------------------------------------


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _seed_demo_credentials() -> tuple[str, str]:
    """Логин и пароль демо-пользователя — те же, что в app/db/seed.py (_DEMO_USER_LOGIN / _DEMO_SEED_PASSWORD)."""
    root = _repo_root()
    if root not in sys.path:
        sys.path.insert(0, root)
    from app.db.seed import _DEMO_SEED_PASSWORD, _DEMO_USER_LOGIN

    return _DEMO_USER_LOGIN, _DEMO_SEED_PASSWORD


def _configure_stdio_utf8() -> None:
    """Чтобы таблица с кириллицей нормально отображалась в консоли Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if not callable(reconf):
            continue
        try:
            reconf(encoding="utf-8")
        except (OSError, ValueError):
            pass


@dataclass(frozen=True)
class DialogCase:
    """case_key — латиница, уникальна; grep по таблице → тот же ключ в кортеже ниже."""

    case_key: str
    category: str  # нежный | средний | сильный
    label: str
    text: str


def _dialogs() -> list[DialogCase]:
    """7 нежных, 7 средней токсичности, 7 сильной (RU, для RuBERT).

    Каждая строка: (case_key, label_ru, text). Искать текст: rg 'case_key' scripts/benchmark_dialogs_predict.py
    """
    gentle: list[tuple[str, str, str]] = [
        (
            "g_weekend",
            "выходные",
            "Марина: Привет! Как прошли выходные?\n"
            "Олег: Спасибо, хорошо — был на даче, посадил пару кустов смородины.\n"
            "Марина: Здорово. Мне тоже надо бы на воздух выбраться.\n"
            "Олег: Давай в следующие выходные сходим в парк, если погода позволит.",
        ),
        (
            "g_work",
            "работа",
            "Антон: Доброе утро, отчёт за квартал я выложил в общую папку.\n"
            "Светлана: Спасибо, посмотрю до обеда и напишу замечания, если будут.\n"
            "Антон: Хорошо, буду на связи.\n"
            "Светлана: Отлично, хорошего дня.",
        ),
        (
            "g_study",
            "учёба",
            "Ира: Ты сделал пятую задачу из списка?\n"
            "Кирилл: Да, вчера вечером. Формулы в методичке понятные.\n"
            "Ира: Супер, тогда завтра разберём шестую вместе.\n"
            "Кирилл: Договорились, спасибо.",
        ),
        (
            "g_family",
            "семья",
            "Бабушка: Внучек, ты поел сегодня?\n"
            "Внук: Да, бабуля, в столовой был — суп и второе.\n"
            "Бабушка: Молодец. Одевайся потеплее, ветер на улице.\n"
            "Внук: Уже надел куртку, не переживай.",
        ),
        (
            "g_shopping",
            "покупки",
            "Продавец: Здравствуйте, вам помочь с размером?\n"
            "Клиент: Да, ищу кроссовки 42 размера, нейтральный цвет.\n"
            "Продавец: Есть две модели, покажу на полке справа.\n"
            "Клиент: Спасибо большое, посмотрю.",
        ),
        (
            "g_weather",
            "погода",
            "Сосед: Слышал, завтра дождь обещают.\n"
            "Соседка: Да, в приложении тоже так. Уберу с балкона рассаду.\n"
            "Сосед: Хорошая мысль. Если что — помогу донести горшки.\n"
            "Соседка: Спасибо, очень приятно.",
        ),
        (
            "g_plans",
            "планы",
            "Лена: Может в субботу сходим в кино?\n"
            "Паша: Давай. На восьмой сеанс нормально?\n"
            "Лена: Да, после обеда как раз успею.\n"
            "Паша: Тогда я куплю билеты заранее онлайн.",
        ),
    ]

    medium: list[tuple[str, str, str]] = [
        (
            "m_late",
            "раздражение",
            "Вика: Ты опять опоздал, мы уже полчаса ждём.\n"
            "Саша: Ну извини, пробки. Не надо так орать.\n"
            "Вика: Мы каждый раз одно и то же слышим.\n"
            "Саша: Ладно, понял, в следующий раз выйду раньше.",
        ),
        (
            "m_modchat",
            "спор",
            "Модератор: Пожалуйста, без перехода на личности.\n"
            "Участник1: Он сам начал нервничать и переводит тему.\n"
            "Участник2: Да ты сам всё переворачиваешь, устал уже.\n"
            "Модератор: Оба успокойтесь, по факту обсуждения.",
        ),
        (
            "m_deadline",
            "работа_напряг",
            "Начальник: Срок горит, где отчёт?\n"
            "Сотрудник: Я же писал, что нужны данные от смежников.\n"
            "Начальник: Не отмахивайся, это твоя зона ответственности.\n"
            "Сотрудник: Ладно, сегодня вечером дотяну как смогу.",
        ),
        (
            "m_neighbors",
            "соседи",
            "А: Музыка у вас до ночи играла, люди спать хотят.\n"
            "Б: Ну не кричи в дверь, можно было написать в чат.\n"
            "А: Писал три раза, ты не отвечал.\n"
            "Б: Ладно, в выходные потише сделаем.",
        ),
        (
            "m_gaming",
            "игра",
            "Игрок1: Ты меня слил, это было подло.\n"
            "Игрок2: Сам тупил, нечего на других сваливать.\n"
            "Игрок1: Очень смешно, в следующий раз без тебя пойду.\n"
            "Игрок2: Как хочешь.",
        ),
        (
            "m_grades",
            "родители",
            "Мама: Опять двойка, когда ты начнёшь стараться?\n"
            "Сын: У меня сложная тема, ты не понимаешь.\n"
            "Мама: Понимаю, что лень — вот что понимаю.\n"
            "Сын: Всё, не хочу сейчас об этом.",
        ),
        (
            "m_owes",
            "друзья",
            "Костя: Ты мне должен был вчера ответить.\n"
            "Дима: Забыл, было много дел, не делай из этого трагедию.\n"
            "Костя: Для тебя всё мелочи, а для меня нет.\n"
            "Дима: Ну извини, окей, напишу почаще.",
        ),
    ]

    strong: list[tuple[str, str, str]] = [
        (
            "s_insults",
            "оскорбления",
            "А: Ты полный идиот, заткнись уже и не лезь не в своё дело.\n"
            "Б: Сам дурак тупой, никто тебя здесь не уважает.\n"
            "А: Вали отсюда, тебя никто не ждал.\n"
            "Б: Сам вали, клоун несчастный.",
        ),
        (
            "s_threats",
            "угрозы_грубые",
            "Хулиган: Если ещё раз сюда придёшь — получишь по морде, понял?\n"
            "Парень: Не трогай меня, я вызову охрану.\n"
            "Хулиган: Делай что хочешь, всё равно тебя найду.\n"
            "Парень: Отстань, псих.",
        ),
        (
            "s_hatewall",
            "ненависть",
            "В чате: Все вы там тупые бараны, один хуже другого.\n"
            "Другой: Заткнись, урод, никто тебя не спрашивал.\n"
            "Первый: Вы все жалкие, сдохните со своими правилами.\n"
            "Другой: Иди лечись, ненормальный.",
        ),
        (
            "s_swear",
            "мат_лёгкий",
            "Один: Чтоб тебя, опять всё сломал.\n"
            "Второй: Да пошёл ты, сам всё ломаешь руками из жопы.\n"
            "Один: Слышь, язык придержи.\n"
            "Второй: Сам придержи, мудак.",
        ),
        (
            "s_troll",
            "троллинг_жёсткий",
            "Тролль: Ты уродина безмозглая, все смеются за твоей спиной.\n"
            "Жертва: Это токсично, прекрати.\n"
            "Тролль: Плачь дальше, никому ты не нужна.\n"
            "Жертва: Блокирую тебя.",
        ),
        (
            "s_driving",
            "агрессия",
            "Водитель: Ты слепой, куда лезешь, я тебя сейчас вытащу из машины!\n"
            "Второй: Попробуй, дебил, я тебя на камеру снимаю.\n"
            "Водитель: Снимай, мне пофиг, ты меня достал.\n"
            "Второй: Иди в баню, хамло.",
        ),
        (
            "s_chat",
            "чат_токсик",
            "Юзер1: ты никчёмное ничтожество иди сдохни\n"
            "Юзер2: сам сдохни урод ебаный\n"
            "Юзер1: я тебя найду и разнесу\n"
            "Юзер2: попробуй засранец",
        ),
    ]

    out: list[DialogCase] = []
    for case_key, label, text in gentle:
        out.append(DialogCase(case_key, "нежный", label, text))
    for case_key, label, text in medium:
        out.append(DialogCase(case_key, "средний", label, text))
    for case_key, label, text in strong:
        out.append(DialogCase(case_key, "сильный", label, text))
    assert len(out) == 21
    return out


def _request_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    token: str | None,
    timeout: float = 120.0,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {url}: {err}") from e


def _login_access_token(base: str, login: str, password: str) -> str:
    url = urljoin(base.rstrip("/") + "/", "auth/login")
    _, payload = _request_json(
        "POST",
        url,
        body={"login": login, "password": password},
        token=None,
    )
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise RuntimeError(f"ожидался {{access_token}}: {payload!r}")
    return str(payload["access_token"])


def _default_model_id(base: str, token: str) -> str:
    url = urljoin(base.rstrip("/") + "/", "predict/models")
    _, models = _request_json("GET", url, token=token)
    if not isinstance(models, list):
        raise RuntimeError(f"ожидался список моделей: {models!r}")
    for m in models:
        if isinstance(m, dict) and m.get("is_default") and m.get("id"):
            return str(m["id"])
    for m in models:
        if isinstance(m, dict) and m.get("id"):
            return str(m["id"])
    raise RuntimeError("пустой каталог моделей")


def _post_predict(base: str, token: str, model_id: str, text: str) -> str:
    url = urljoin(base.rstrip("/") + "/", "predict")
    _, payload = _request_json("POST", url, token=token, body={"model_id": model_id, "text": text})
    if not isinstance(payload, dict) or not payload.get("task_id"):
        raise RuntimeError(f"ожидался {{task_id}}: {payload!r}")
    return str(payload["task_id"])


def _get_task(base: str, token: str, task_id: str) -> dict[str, Any]:
    url = urljoin(base.rstrip("/") + "/", f"predict/{task_id}")
    _, payload = _request_json("GET", url, token=token)
    assert isinstance(payload, dict)
    return payload


def _poll_task(
    base: str,
    token: str,
    task_id: str,
    *,
    deadline_sec: float,
    interval: float,
) -> dict[str, Any]:
    end = time.monotonic() + deadline_sec
    last: dict[str, Any] = {}
    while time.monotonic() < end:
        last = _get_task(base, token, task_id)
        st = str(last.get("status", ""))
        if st in ("completed", "failed"):
            return last
        time.sleep(interval)
    raise TimeoutError(f"task_id={task_id} за {deadline_sec}s остался status={last.get('status')!r}")


def _fmt_prob(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, (int, float)):
        return f"{float(v):.4f}"
    try:
        return f"{float(Decimal(str(v))):.4f}"
    except Exception:
        return str(v)


def _truncate(s: str, max_len: int) -> str:
    s = s.replace("\n", " ↵ ")
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _how_it_went(category: str, is_toxic: bool | None) -> str:
    """Коротко: как отработала модель относительно типа диалога."""
    if is_toxic is None:
        return "нет ответа"
    if category == "нежный":
        return "ОК, мягкий текст" if not is_toxic else "ложняя токсичность"
    if category == "средний":
        return "не токс. (спорно)" if not is_toxic else "поймали накал"
    if category == "сильный":
        return "пропуск грязи" if not is_toxic else "ОК, грязь поймана"
    return "—"


def main() -> int:
    _configure_stdio_utf8()
    base = BASE_URL.rstrip("/")
    token = (ACCESS_TOKEN.strip() or os.environ.get("ACCESS_TOKEN", "").strip())
    if not token:
        try:
            demo_login, demo_password = _seed_demo_credentials()
            token = _login_access_token(base, demo_login, demo_password)
        except Exception as e:
            print(
                "Нет ACCESS_TOKEN и не удалось выполнить POST /auth/login "
                f"учёткой из app/db/seed.py: {e}",
                file=sys.stderr,
            )
            return 2
        print(f"Авторизация: POST /auth/login ({demo_login})\n")
    else:
        print("Авторизация: готовый ACCESS_TOKEN\n")

    try:
        model_id = _default_model_id(base, token)
    except Exception as e:
        print(f"Не удалось получить модель: {e}", file=sys.stderr)
        return 2

    print(f"BASE_URL={base}\nmodel_id (default)={model_id}\n")

    dialogs = _dialogs()
    rows: list[tuple[DialogCase, str, dict[str, Any]]] = []

    for i, d in enumerate(dialogs, start=1):
        print(
            f"[{i}/21] case_key={d.case_key} POST predict «{d.category}/{d.label}»…",
            flush=True,
        )
        tid = _post_predict(base, token, model_id, d.text)
        print(f"       task_id={tid}, ждём результат…", flush=True)
        try:
            result = _poll_task(
                base,
                token,
                tid,
                deadline_sec=POLL_DEADLINE_PER_TASK_SEC,
                interval=POLL_INTERVAL_SEC,
            )
        except TimeoutError as e:
            print(f"       ОШИБКА: {e}", file=sys.stderr)
            result = {"status": "timeout", "error": str(e)}
        rows.append((d, tid, result))

    # таблица: case_key совпадает с первой строкой кортежа в _dialogs() — удобно rg по скрипту
    col_key = 12
    col_cat = 10
    col_lab = 12
    col_tox = 8
    col_prob = 8
    col_st = 9
    col_hint = 26
    col_snip = 32

    sep = (
        "+"
        + "-" * 4
        + "+"
        + "-" * col_key
        + "+"
        + "-" * col_cat
        + "+"
        + "-" * col_lab
        + "+"
        + "-" * col_tox
        + "+"
        + "-" * col_prob
        + "+"
        + "-" * col_st
        + "+"
        + "-" * col_hint
        + "+"
        + "-" * col_snip
        + "+"
    )
    print("\n" + sep)
    print(
        f"| {'№':^2} | {'case_key':^{col_key}} | {'Диалог':^{col_cat-2}} | "
        f"{'Сценарий':^{col_lab-2}} | "
        f"{'is_toxic':^{col_tox-2}} | {'p_tox':^{col_prob-2}} | {'status':^{col_st-2}} | "
        f"{'Как отработало':^{col_hint-2}} | {'Фрагмент':^{col_snip-2}} |"
    )
    print(sep)

    for i, (d, tid, r) in enumerate(rows, start=1):
        st = str(r.get("status", ""))
        it = r.get("is_toxic")
        it_s = "—" if it is None else ("да" if it else "нет")
        prob = _fmt_prob(r.get("toxicity_probability"))
        snip = _truncate(d.text, col_snip)
        hint = _how_it_went(d.category, it if isinstance(it, bool) else None)
        print(
            f"| {i:2d} | {d.case_key[:col_key]:<{col_key}} | "
            f"{d.category[:col_cat]:<{col_cat}} | {d.label[:col_lab]:<{col_lab}} | "
            f"{it_s:^{col_tox}} | {prob:^{col_prob}} | {st[:col_st]:<{col_st}} | "
            f"{hint[:col_hint]:<{col_hint}} | {snip:<{col_snip}} |"
        )
    print(sep)

    print(
        "\nЛегенда «Как отработало»: для нежного ждём не токс.; для среднего — ок и так и так; "
        "для сильного ждём токс.=да. Колонка «Диалог» = задуманная грязность текста."
    )
    print(
        "Колонка «p_tox» = toxicity_probability. Полный summary ниже по task_id.\n"
        "Связь с кодом: скопируйте case_key из таблицы и выполните, например:\n"
        '  rg "m_neighbors" scripts/benchmark_dialogs_predict.py'
    )
    for i, (d, tid, r) in enumerate(rows, start=1):
        summ = r.get("result_summary")
        if summ:
            print(
                f"\n--- [{i}] case_key={d.case_key} {d.category}/{d.label} "
                f"task_id={tid} ---\n{summ}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
