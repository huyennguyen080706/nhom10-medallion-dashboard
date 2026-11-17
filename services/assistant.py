"""Trợ lý hỏi đáp tiếng Việt trên tầng Gold và tầng mô hình.

Mô hình ngôn ngữ chỉ được làm một việc với kho: gọi công cụ `chay_sql` với một câu SELECT.
Mọi câu SQL đi qua ba lớp chặn trước khi chạy thật:
  1. chạy thử (dry run) để BigQuery tự báo loại câu lệnh: chỉ nhận SELECT;
  2. mọi bảng được tham chiếu phải thuộc gold / ml của kho này;
  3. giới hạn số byte quét (dry run và maximum_bytes_billed).
Khoá API đọc từ biến môi trường ANTHROPIC_API_KEY hoặc file .env (đã nằm trong .gitignore).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

PROJECT = "project-k244161774"
SUFFIX = os.environ.get("DW_SUFFIX", "_v2")
GOLD, ML = f"{PROJECT}.gold{SUFFIX}", f"{PROJECT}.ml{SUFFIX}"
DATASET_DUOC_PHEP = {f"gold{SUFFIX}", f"ml{SUFFIX}"}
MODEL = os.environ.get("ASSISTANT_MODEL", "claude-opus-5-5")
BYTE_TOI_DA = 300 * 1024 * 1024        # 300 MB cho một câu hỏi
DONG_CHO_MO_HINH = 60                  # số dòng kết quả gửi lại mô hình
DONG_HIEN_THI = 2000
SO_VONG_TOI_DA = 6
ROOT = Path(__file__).resolve().parents[2]

QUY_TAC = """Bạn là trợ lý phân tích dữ liệu của một kho dữ liệu chứng khoán Việt Nam phục vụ học tập.
Người hỏi là sinh viên và giảng viên ngành kinh tế, không nhất thiết biết SQL.

Cách làm việc:
- Muốn biết số liệu thì phải gọi công cụ chay_sql với một câu SELECT của BigQuery. Không bao giờ nêu con số
  mà không lấy từ kết quả truy vấn trong cuộc trò chuyện này.
- Mỗi câu hỏi nên trả lời bằng một hoặc hai truy vấn gọn. Nếu truy vấn lỗi thì đọc thông báo lỗi và sửa.
- Chỉ đọc được các bảng liệt kê bên dưới. Kho từ chối mọi lệnh không phải SELECT.
- Kết quả dài thì thêm ORDER BY và LIMIT hợp lý (mặc định không quá 50 dòng) vì người đọc xem trên bảng.
- Trả lời bằng tiếng Việt, ngắn gọn: câu trả lời trước, sau đó một hai câu giải thích cách tính và đơn vị.
  Không lặp lại cả bảng kết quả vì giao diện đã hiện bảng; chỉ nêu các con số chính.
- Nếu câu hỏi mơ hồ, chọn cách hiểu hợp lý nhất và nói rõ mình đã hiểu thế nào.
- Nếu kho không có dữ liệu để trả lời thì nói thẳng là không có, không đoán.
- Đây là công cụ theo dõi rủi ro phục vụ học tập. Không đưa ra khuyến nghị mua bán. Nếu được hỏi nên mua hay bán
  mã nào, hãy đưa số liệu liên quan và nói rõ đây không phải khuyến nghị đầu tư."""

CONG_CU = [{
    "name": "chay_sql",
    "description": ("Chạy một câu SELECT (BigQuery Standard SQL) trên kho và trả về kết quả dạng CSV. "
                    "Chỉ đọc được bảng thuộc tầng Gold và tầng mô hình. Gọi công cụ này mỗi khi cần số liệu."),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "Một câu SELECT duy nhất, tên bảng viết đủ dạng `project.dataset.table`."},
            "muc_dich": {"type": "string", "description": "Một câu tiếng Việt nói truy vấn này lấy gì."},
        },
        "required": ["sql", "muc_dich"],
        "additionalProperties": False,
    },
    "strict": True,
}]


def lop_ngu_nghia() -> str:
    txt = (Path(__file__).with_name("semantic_layer.md")).read_text(encoding="utf-8")
    return txt.replace("{GOLD}", GOLD).replace("{ML}", ML)


def chi_luoc_do(client: bigquery.Client) -> str:
    """Phương án đối chứng: chỉ tên bảng và tên cột lấy từ INFORMATION_SCHEMA, không có mô tả."""
    dong = ["# Danh sách bảng và cột"]
    for ds in sorted(DATASET_DUOC_PHEP):
        q = (f"SELECT table_name, STRING_AGG(column_name || ' ' || data_type, ', ' ORDER BY ordinal_position) c "
             f"FROM `{PROJECT}.{ds}.INFORMATION_SCHEMA.COLUMNS` GROUP BY 1 ORDER BY 1")
        for r in client.query(q).result():
            dong.append(f"- `{PROJECT}.{ds}.{r.table_name}`: {r.c}")
    return "\n".join(dong)


def he_thong(tai_lieu: str) -> list[dict]:
    # Phần hệ thống không đổi giữa các câu hỏi nên đặt điểm lưu bộ nhớ đệm ở cuối.
    return [{"type": "text", "text": QUY_TAC + "\n\n" + tai_lieu, "cache_control": {"type": "ephemeral"}}]


class SqlBiTuChoi(Exception):
    pass


def kiem_sql(sql: str, client: bigquery.Client) -> int:
    """Trả về số byte sẽ quét nếu câu lệnh hợp lệ; ném SqlBiTuChoi nếu không."""
    s = re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql, flags=re.S).strip().rstrip(";").strip()
    if not s:
        raise SqlBiTuChoi("Câu lệnh rỗng.")
    if ";" in s:
        raise SqlBiTuChoi("Chỉ nhận một câu lệnh; không dùng dấu chấm phẩy ở giữa.")
    if not re.match(r"(?is)^\(*\s*(select|with)\b", s):
        raise SqlBiTuChoi("Chỉ nhận câu lệnh SELECT.")
    try:
        job = client.query(s, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False))
    except Exception as e:  # lỗi cú pháp, sai tên bảng, sai tên cột
        loi = getattr(e, "errors", None)
        raise SqlBiTuChoi("BigQuery báo lỗi: " + str(loi[0].get("message") if loi else e).split("\n")[0][:600])
    if job.statement_type != "SELECT":
        raise SqlBiTuChoi(f"Chỉ nhận SELECT, câu này là {job.statement_type}.")
    for t in job.referenced_tables or []:
        if t.project != PROJECT or t.dataset_id not in DATASET_DUOC_PHEP:
            raise SqlBiTuChoi(f"Không được đọc `{t.project}.{t.dataset_id}.{t.table_id}`; chỉ đọc tầng Gold và tầng mô hình.")
    nbyte = int(job.total_bytes_processed or 0)
    if nbyte > BYTE_TOI_DA:
        raise SqlBiTuChoi(f"Truy vấn quét {nbyte / 1e6:.0f} MB, vượt giới hạn {BYTE_TOI_DA / 1e6:.0f} MB. Thu hẹp cột hoặc khoảng ngày.")
    return nbyte


def chay_sql(sql: str, client: bigquery.Client) -> tuple[pd.DataFrame, int]:
    nbyte = kiem_sql(sql, client)
    s = re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql, flags=re.S).strip().rstrip(";")
    job = client.query(s, job_config=bigquery.QueryJobConfig(maximum_bytes_billed=BYTE_TOI_DA))
    df = job.result(max_results=DONG_HIEN_THI).to_dataframe(create_bqstorage_client=False)
    return df, nbyte


def _csv_cho_mo_hinh(df: pd.DataFrame) -> str:
    dau = df.head(DONG_CHO_MO_HINH).to_csv(index=False, float_format="%.6g")
    if len(df) > DONG_CHO_MO_HINH:
        dau += f"\n(kết quả có {len(df)} dòng, chỉ hiện {DONG_CHO_MO_HINH} dòng đầu)"
    if df.empty:
        dau = "(không có dòng nào)"
    return dau


@dataclass
class Buoc:
    sql: str
    muc_dich: str
    df: pd.DataFrame | None = None
    loi: str | None = None
    byte_quet: int = 0


@dataclass
class TraLoi:
    van_ban: str = ""
    cac_buoc: list[Buoc] = field(default_factory=list)
    token_vao: int = 0
    token_ra: int = 0
    token_doc_dem: int = 0
    token_ghi_dem: int = 0
    so_lan_goi: int = 0
    ly_do_dung: str = ""

    @property
    def bang_cuoi(self) -> pd.DataFrame | None:
        ok = [b for b in self.cac_buoc if b.df is not None]
        return ok[-1].df if ok else None


def tai_khoa() -> bool:
    """Nạp .env nếu có; trả về True nếu đã có khoá. Không in, không trả giá trị khoá."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env")
        except Exception:
            pass
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def hoi(cau_hoi: str, lich_su: list[dict] | None = None, tai_lieu: str | None = None,
        bq: bigquery.Client | None = None, llm=None) -> TraLoi:
    """Một lượt hỏi đáp. `lich_su` là các lượt trước dạng [{'role','content': str}]."""
    import anthropic

    from services.gcp_auth import make_client

    bq = bq or make_client(PROJECT)
    llm = llm or anthropic.Anthropic()
    tin = [*(lich_su or []), {"role": "user", "content": cau_hoi}]
    kq = TraLoi()
    he = he_thong(tai_lieu if tai_lieu is not None else lop_ngu_nghia())
    for _ in range(SO_VONG_TOI_DA):
        r = llm.messages.create(model=MODEL, max_tokens=8000, system=he, tools=CONG_CU, messages=tin)
        kq.so_lan_goi += 1
        kq.token_vao += r.usage.input_tokens
        kq.token_ra += r.usage.output_tokens
        kq.token_doc_dem += getattr(r.usage, "cache_read_input_tokens", 0) or 0
        kq.token_ghi_dem += getattr(r.usage, "cache_creation_input_tokens", 0) or 0
        kq.ly_do_dung = r.stop_reason
        tin.append({"role": "assistant", "content": r.content})
        if r.stop_reason != "tool_use":
            kq.van_ban = "\n".join(b.text for b in r.content if b.type == "text").strip()
            if r.stop_reason == "refusal" and not kq.van_ban:
                kq.van_ban = "Trợ lý từ chối trả lời câu hỏi này."
            return kq
        ket_qua = []
        for b in r.content:
            if b.type != "tool_use":
                continue
            sql = str(b.input.get("sql", ""))
            buoc = Buoc(sql=sql, muc_dich=str(b.input.get("muc_dich", "")))
            try:
                buoc.df, buoc.byte_quet = chay_sql(sql, bq)
                noi_dung, loi = _csv_cho_mo_hinh(buoc.df), False
            except SqlBiTuChoi as e:
                buoc.loi, noi_dung, loi = str(e), str(e), True
            except Exception as e:
                buoc.loi = "Lỗi khi chạy: " + str(e).split("\n")[0][:600]
                noi_dung, loi = buoc.loi, True
            kq.cac_buoc.append(buoc)
            ket_qua.append({"type": "tool_result", "tool_use_id": b.id, "content": noi_dung, "is_error": loi})
        tin.append({"role": "user", "content": ket_qua})
    kq.van_ban = "Trợ lý đã dùng hết số lượt truy vấn cho phép mà chưa ra câu trả lời. Hãy hỏi cụ thể hơn."
    return kq
