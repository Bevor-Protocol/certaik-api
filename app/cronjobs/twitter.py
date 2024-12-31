# TODO: Integrate cron job that checks for recent tweets and replies to then with an audit.
# Make sure to change the starting messages contents so the tweets aren't hidden for spam.

def compose_tweet_message(twitter_handle: str, coin_name: str, summary: dict) -> str:
    return (
        f"Hi @{twitter_handle}!\n\n"
        "You are trending right now on CoinGecko!📈\n\n"
        "We audited your contract to help you:\n\n"
        f"🔴 Critical Severity Issues: {summary['critical']}\n"
        f"🟠 High Severity Issues: {summary['high']}\n"
        f"🟡 Medium Severity Issues: {summary['medium']}\n"
        f"🟢 Low Severity Issues: {summary['low']}\n\n"
        "For more details, visit https://certaik.xyz and audit your contract.\n\n"
        f"#{coin_name.replace(' ', '')} #Crypto #CertaiK #Audit"
    )

async def post_tweet(message: str):
    try:
        await twitter_client.v2.tweet(message)
        print('Tweet posted successfully.')
    except Exception as error:
        print('Error posting tweet:', error)