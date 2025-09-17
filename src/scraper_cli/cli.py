from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich import box
from .config import ScraperConfig, write_default_config
from .db import DB
from .fetcher import crawl
from .summarizer import summarize_text

app = typer.Typer(help="Modern interactive web scraper CLI")
console = Console()

@app.command()
def init(
    config_path: Path = typer.Option("config.json", exists=False, help="Where to create config"),
    db_path: Path = typer.Option("scraper.db", help="SQLite file"),
):
    """Create default config and SQLite DB."""
    write_default_config(config_path)
    DB(db_path).close()
    console.print(f"[green]Created[/green] {config_path} and {db_path}")

@app.command()
def run(
    config_path: Path = typer.Option("config.json", exists=True),
    db_path: Path = typer.Option("scraper.db"),
    max_pages: Optional[int] = typer.Option(None, help="Stop after N pages"),
    depth: Optional[int] = typer.Option(None, help="Override max_depth in config"),
):
    """Run crawler (fetch + parse)."""
    cfg = ScraperConfig.load(config_path)
    if depth is not None:
        cfg.max_depth = depth
    db = DB(db_path)
    try:
        asyncio.run(crawl(cfg, db, max_pages=max_pages))
    finally:
        db.close()
    console.print("[green]Done.[/green]")

@app.command()
def summarize(
    db_path: Path = typer.Option("scraper.db"),
    url: Optional[str] = typer.Option(None, help="Page URL to summarize"),
    scope_collection: bool = typer.Option(False, help="Summarize across all pages (collection)"),
    sentences: int = typer.Option(5, help="Number of sentences")
):
    """Create extractive summaries."""
    db = DB(db_path)
    cur = db.conn.cursor()

    if scope_collection:
        cur.execute("SELECT html FROM pages WHERE html IS NOT NULL AND error IS NULL")
        texts = [r["html"] or "" for r in cur.fetchall()]
        text = "\n".join(texts)[:1_000_000]  # clamp
        summ = summarize_text(text, sentences)
        db.insert_summary(scope="collection", key="all", text=summ)
        console.print(summ)
    elif url:
        cur.execute("SELECT html FROM pages WHERE url = ?", (url,))
        row = cur.fetchone()
        if not row or not row["html"]:
            typer.echo("No HTML found for that URL")
            raise typer.Exit(code=1)
        summ = summarize_text(row["html"], sentences)
        db.insert_summary(scope="page", key=url, text=summ)
        console.print(summ)
    else:
        typer.echo("Provide --url or --scope-collection")
        raise typer.Exit(code=2)
    db.close()

@app.command("stats")
def stats_cmd(
    db_path: Path = typer.Option("scraper.db")
):
    """Show DB stats."""
    db = DB(db_path)
    s = db.stats()
    table = Table(title="Scraper Stats", box=box.SIMPLE)
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    for k, v in s.items():
        table.add_row(k, str(v))
    console.print(table)
    db.close()

@app.command()
def export(
    db_path: Path = typer.Option("scraper.db"),
    outfile: Path = typer.Option("items.json"),
    fmt: str = typer.Option("json", help="json|csv")
):
    """Export extracted items."""
    import csv
    db = DB(db_path)
    cur = db.conn.cursor()
    cur.execute("SELECT data_json FROM items")
    rows = [json.loads(r["data_json"]) for r in cur.fetchall()]
    db.close()

    if fmt == "json":
        outfile.write_text(json.dumps(rows, indent=2))
        console.print(f"[green]Wrote[/green] {outfile}")
        return

    # CSV: flatten keys
    keys = sorted({k for r in rows for k in r.keys()})
    with outfile.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})
    console.print(f"[green]Wrote[/green] {outfile}")

@app.command()
def query(
    db_path: Path = typer.Option("scraper.db"),
    sql: str = typer.Argument(..., help="SELECT ..."),
    limit: int = typer.Option(25)
):
    """Run a quick SELECT query and pretty-print."""
    db = DB(db_path)
    cur = db.conn.cursor()
    cur.execute(sql)
    rows = cur.fetchmany(limit)
    if not rows:
        console.print("[yellow]No rows[/yellow]")
        return
    columns = rows[0].keys()
    table = Table(box=box.MINIMAL_HEAVY_HEAD)
    for c in columns:
        table.add_column(c)
    for r in rows:
        table.add_row(*[str(r[c]) if r[c] is not None else "" for c in columns])
    console.print(table)
    db.close()

def main():
    app()

if __name__ == "__main__":
    main()
