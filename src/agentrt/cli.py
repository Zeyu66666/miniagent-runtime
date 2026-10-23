import typer
app = typer.Typer(help="miniagent-runtime")
@app.command()
def hello():
    """测试命令是否可用"""
    print("agentrt 装好了")

@app.callback()
def main():
    """miniagent-runtime CLI"""

if __name__ == "__main__":
    app()