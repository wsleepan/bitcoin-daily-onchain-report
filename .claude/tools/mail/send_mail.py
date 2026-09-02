# -*- coding: utf-8 -*-
"""산출물 메일 발송.

설계 원칙
  · 자격증명은 프로젝트 폴더 밖에 둔다. 클라우드 동기화·git 커밋 사고를 막는다.
  · 첨부는 '현재 작업 폴더 안'의 파일만 허용한다. 실수로 아무 파일이나
    나가지 않게 하는 1차 방어선이다.
  · --test 는 발신 계정 본인에게만 간다. 이 제약은 절대 완화하지 않는다.
  · 보낸 것은 전부 SHA-256 과 함께 기록한다. 나중에 "그때 보낸 게 이 파일이 맞나"를
    해시로 대조할 수 있어야 한다.

사용법
  python send_mail.py --file <경로> --to <주소> --subject "<제목>" [--body "<본문>"]
  python send_mail.py --file a.docx --file b.xlsx --to x@y.com --subject "..." --dry-run
  python send_mail.py --test --file <경로> --subject "..."      # 본인에게만
  python send_mail.py --status                                   # 설정 확인
"""
import argparse
import datetime
import hashlib
import io
import json
import mimetypes
import os
import pathlib
import smtplib
import sys
from email.message import EmailMessage

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

HOME = pathlib.Path(os.environ.get("USERPROFILE") or os.path.expanduser("~"))
CONF_CANDIDATES = [
    HOME / ".claude" / "mail" / "config.json",   # 표준 위치
    HOME / ".khnp_mail" / "config.json",         # 이전 위치(하위호환)
]
GLOBAL_LOG = HOME / ".claude" / "mail" / "send_log.md"
MAX_ATTACH = 25 * 1024 * 1024                    # Gmail 한도


def find_conf():
    for p in CONF_CANDIDATES:
        if p.exists():
            return p
    return None


def load_conf():
    p = find_conf()
    if p is None:
        sys.exit(
            "[중단] 자격증명이 없다.\n"
            "       ~/.claude/mail/config.json 에 sender / app_password 를 넣을 것.\n"
            "       Gmail 앱 비밀번호는 2단계 인증을 켠 뒤 발급한다(16자리).")
    conf = json.loads(p.read_text(encoding="utf-8-sig"))
    for k in ("sender", "app_password"):
        if not conf.get(k):
            sys.exit("[중단] %s 에 '%s' 가 비어 있다." % (p, k))
    conf["_path"] = str(p)
    return conf


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def project_log():
    """프로젝트 쪽 기록 위치. 관행적인 경로가 있으면 거기에, 없으면 작업 폴더에."""
    cwd = pathlib.Path.cwd()
    for rel in ("analysis/findings", "docs", "outputs"):
        d = cwd / rel
        if d.is_dir():
            return d / "메일발송_이력.md"
    return cwd / "메일발송_이력.md"


def cmd_status():
    p = find_conf()
    print("자격증명 : %s" % (p if p else "없음 — config.json 을 먼저 만들 것"))
    if p:
        c = json.loads(p.read_text(encoding="utf-8-sig"))
        print("발신     : %s" % c.get("sender"))
        print("기본수신 : %s" % (c.get("recipient") or "(없음)"))
        al = c.get("allowed_recipients")
        print("허용목록 : %s" % (", ".join(al) if al else "(제한 없음)"))
    print("작업폴더 : %s" % pathlib.Path.cwd())
    print("기록     : %s" % project_log())
    print("전체기록 : %s" % GLOBAL_LOG)


def check_attachment(path, cwd):
    f = pathlib.Path(path).resolve()
    if not f.is_file():
        sys.exit("[중단] 파일이 없다: %s" % f)
    if cwd not in f.parents and f.parent != cwd:
        sys.exit(
            "[중단] 현재 작업 폴더 밖의 파일은 보내지 않는다.\n"
            "       파일   : %s\n"
            "       작업폴더: %s\n"
            "       보내야 한다면 먼저 작업 폴더 안으로 복사할 것." % (f, cwd))
    return f


def main():
    ap = argparse.ArgumentParser(description="산출물 메일 발송", add_help=True)
    ap.add_argument("--status", action="store_true", help="설정 확인 후 종료")
    ap.add_argument("--file", action="append", default=[], help="첨부(여러 번 가능)")
    ap.add_argument("--to", help="수신자. 쉼표로 여러 명")
    ap.add_argument("--cc", help="참조")
    ap.add_argument("--subject", help="제목")
    ap.add_argument("--body", help="본문")
    ap.add_argument("--body-file", dest="body_file", help="본문을 읽어올 파일")
    ap.add_argument("--dry-run", action="store_true", help="보내지 않고 출력만")
    ap.add_argument("--test", action="store_true", help="발신 계정 본인에게만")
    ap.add_argument("--force-recipient", action="store_true",
                    help="allowed_recipients 밖으로 보낼 때")
    a = ap.parse_args()

    if a.status:
        cmd_status()
        return
    if not a.subject:
        sys.exit("[중단] --subject 가 필요하다.")

    conf = load_conf()
    cwd = pathlib.Path.cwd().resolve()

    # 수신자 결정
    if a.test:
        if a.to and a.to.strip() != conf["sender"]:
            sys.exit(
                "[중단] --test 는 발신 계정 본인(%s)에게만 보낼 수 있다.\n"
                "       외부 수신자에게 보내려면 --test 없이 --to 로 보낼 것.\n"
                "       이 제약은 완화하지 않는다." % conf["sender"])
        to = conf["sender"]
    else:
        to = a.to or conf.get("recipient")
        if not to:
            sys.exit("[중단] --to 가 없고 설정에도 기본 수신자가 없다.")

    allowed = conf.get("allowed_recipients")
    if allowed and not a.test and not a.force_recipient:
        outside = [x.strip() for x in to.split(",")
                   if x.strip() and x.strip() not in allowed]
        if outside:
            sys.exit(
                "[중단] 허용 목록에 없는 수신자다: %s\n"
                "       허용 목록: %s\n"
                "       의도한 발송이면 --force-recipient 를 붙일 것."
                % (", ".join(outside), ", ".join(allowed)))

    # 첨부 검사
    files, total = [], 0
    for p in a.file:
        f = check_attachment(p, cwd)
        files.append(f)
        total += f.stat().st_size
    if total > MAX_ATTACH:
        sys.exit("[중단] 첨부 합계가 Gmail 한도(25MB)를 넘는다: %.1f MB" % (total / 1e6))

    digests = [(f, sha256(f)) for f in files]

    # 본문
    if a.body_file:
        body = pathlib.Path(a.body_file).read_text(encoding="utf-8")
    elif a.body:
        body = a.body
    elif files:
        lines = ["첨부와 같이 보내드립니다.", ""]
        for f, d in digests:
            lines += [
                "  · 파일명   : %s" % f.name,
                "  · 크기     : %.1f MB" % (f.stat().st_size / 1e6),
                "  · SHA-256  : %s" % d,
                "  · 생성일시 : %s" % datetime.datetime.fromtimestamp(
                    f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                "",
            ]
        body = "\n".join(lines)
    else:
        sys.exit("[중단] 첨부도 본문도 없다.")

    subject = ("[테스트] " if a.test else "") + a.subject

    msg = EmailMessage()
    msg["From"] = conf["sender"]
    msg["To"] = to
    if a.cc:
        msg["Cc"] = a.cc
    msg["Subject"] = subject
    msg.set_content(body)
    for f, _ in digests:
        ctype, _enc = mimetypes.guess_type(f.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(f.read_bytes(), maintype=maintype, subtype=subtype,
                           filename=f.name)

    print("모드 : %s" % ("시험 발송(본인 수신)" if a.test else "정식 발송"))
    print("발신 : %s" % conf["sender"])
    print("수신 : %s%s" % (to, ("  (참조 %s)" % a.cc) if a.cc else ""))
    print("제목 : %s" % subject)
    for f, d in digests:
        print("첨부 : %s (%.1f MB)  %s" % (f.name, f.stat().st_size / 1e6, d))
    if not files:
        print("첨부 : 없음")

    if a.dry_run:
        print("\nDRY RUN — 실제 발송하지 않았다.")
        return

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=180) as s:
        s.starttls()
        s.login(conf["sender"], conf["app_password"])
        s.send_message(msg)

    now = datetime.datetime.now().isoformat(timespec="seconds")
    names = ", ".join("`%s`" % f.name for f, _ in digests) or "(첨부 없음)"
    short = ", ".join(d[:16] for _, d in digests) or "-"
    line = "- %s — %s%s → %s (SHA-256 %s)\n" % (
        now, "[시험] " if a.test else "", names, to, short)
    for log in (project_log(), GLOBAL_LOG):
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            with io.open(log, "a", encoding="utf-8") as fh:
                fh.write(line)
        except Exception as e:
            print("  [경고] 기록 실패 %s: %s" % (log, e))
    print("\n발송 완료: %s" % now)


if __name__ == "__main__":
    main()
