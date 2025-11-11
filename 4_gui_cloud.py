#lib
import os, asyncio, feedparser
import streamlit as st
from strands import Agent, tool

# Streamlitシークレットを環境変数に設定
os.environ['AWS_ACCESS_KEY_ID'] = st.secrets['AWS_ACCESS_KEY_ID']
os.environ['AWS_SECRET_ACCESS_KEY'] = st.secrets['AWS_SECRET_ACCESS_KEY']
os.environ['AWS_DEFAULY_REGION'] = st.secrets['AWS_DEFAULT_REGION']

#ツール定義
@tool
def get_aws_updates(service_name: str) -> list:
    #AWS What's new のRSSフィードをパース
    feed = feedparser.parse("https://aws.amazon.com/about-aws/whats-new/recent/feed/")
    result = []

    #フィードの各エントリをチェック
    for entry in feed.entries:
        if service_name.lower() in entry.title.lower():
            result.append({
                "published": entry.get("published", "N/A"),
                "summary": entry.get("summary", "")
            })

            #最大3件
            if len(result) >= 3:
                break
    return result

#エージェント
agent = Agent(
    model="arn:aws:bedrock:us-west-2:591570009439:inference-profile/global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    tools=[get_aws_updates]
)

# ページタイトルと入力欄を表示
st.title("AWSアップデート確認くん")
service_name = st.text_input("アップデートを知りたいAWSサービス名を入力してください：")

# 非同期ストリーミング処理
async def process_stream(service_name, container):
    text_holder = container.empty()
    response = ""
    prompt = f"AWSの{service_name.strip()}の最新アップデートを、日付つきで要約して。"
    
    # エージェントからのストリーミングレスポンスを処理    
    async for chunk in agent.stream_async(prompt):
        if isinstance(chunk, dict):
            event = chunk.get("event", {})

            # ツール実行を検出して表示
            if "contentBlockStart" in event:
                tool_use = event["contentBlockStart"].get("start", {}).get("toolUse", {})
                tool_name = tool_use.get("name")
                
                # バッファをクリア
                if response:
                    text_holder.markdown(response)
                    response = ""

                # ツール実行のメッセージを表示
                container.info(f"🔧 {tool_name} ツールを実行中…")
                text_holder = container.empty()
            
            # テキストを抽出してリアルタイム表示
            if text := chunk.get("data"):
                response += text
                text_holder.markdown(response)

# ボタンを押したら生成開始
if st.button("確認"):
    if service_name:
        with st.spinner("アップデートを確認中..."):
            container = st.container()
            asyncio.run(process_stream(service_name, container))