import os
import requests

GPTZ_API_KEY = os.getenv("GPTZ_API_KEY")
COOKIE_DAO_API_KEY = os.getenv("COOKIE_API_KEY")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_TOKEN")


class AgentSecurityService:
    def __init__(self):
        pass

    def get_agent_by_twitter(
        self, twitter_username: str, interval: str = "_7Days"
    ) -> dict:
        """
        Get agent details from Cookie API by Twitter username

        Args:
            twitter_username (str): Twitter username to lookup
            interval (str, optional): Time interval for metrics. Defaults to "_7Days"

        Returns:
            dict: Agent details including metrics and social data
        """

        url = f"https://api.cookie.fun/v2/agents/twitterUsername/{twitter_username}"
        params = {"interval": interval}
        headers = {"x-api-key": COOKIE_DAO_API_KEY}

        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        return response.json()

    def get_last_agent_tweets(self, username: str) -> str:
        """
        Get the text from the last 3 tweets from the X API for a specific agent

        Args:
            username (str): Twitter username to lookup tweets for

        Returns:
            str: Combined text from the last 3 tweets
        """
        # Correct the URL to the appropriate endpoint for fetching user details
        url = f"https://api.twitter.com/2/users/by/username/{username}"
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}

        # First get user ID
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        user_id = response.json()["data"]["id"]

        print(f"User ID: {user_id}")

        # Then get tweets
        tweets_url = f"https://api.x.com/2/users/{user_id}/tweets"
        params = {"max_results": 15}

        response = requests.get(tweets_url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()

        # Clean data by removing @ mentions
        # First check if 'data' exists in response
        if "data" not in data:
            return ""

        # Get tweets text and clean them
        tweets = data["data"]
        if not isinstance(tweets, list):
            return ""

        # Clean each tweet by removing @ mentions
        cleaned_tweets = []
        for tweet in tweets:
            if "text" in tweet:
                words = tweet["text"].split()
                cleaned_words = [word for word in words if not word.startswith("@")]
                cleaned_tweets.append(" ".join(cleaned_words))

        # Combine cleaned tweets
        combined_text = " ".join(cleaned_tweets)

        return combined_text

    def get_ai_probability(self, text: str) -> float:
        """
        Get the probability that a text is AI generated using the GPTZero API

        Args:
            text (str): Text to analyze

        Returns:
            float: Probability between 0 and 1 that the text is AI generated
        """
        url = "https://api.gptzero.me/v2/predict/text"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-key": GPTZ_API_KEY,
        }
        data = {"document": text, "multilingual": False}

        response = requests.post(url, headers=headers, json=data)

        # Check for HTTP errors
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            print(f"Response content: {response.content}")
            return 0.0  # Return a default value or handle as needed

        result = response.json()

        # Get the AI probability from the first document's class probabilities
        ai_prob = result["documents"][0]["class_probabilities"]["ai"]

        return ai_prob

    def calculate_agent_sec_score(
        self, twitter_username: str, smart_contract_audit_score: float
    ) -> float:
        """
        Calculate the Agent Security Score based on multiple factors

        Args:
            twitter_username (str): Twitter username of the agent
            smart_contract_audit_score (float): Score from 0-100 based on smart contract audits

        Returns:
            float: Security score from 0-100
        """
        import math

        # Get agent data
        agent_data = self.get_agent_by_twitter(twitter_username)

        # Get mindshare percentage (0-100)
        mindshare_pct = min(max(agent_data["ok"]["mindshare"] * 100, 0), 100)

        # Get market cap and cap it at 10B
        market_cap = min(agent_data["ok"]["marketCap"], 10_000_000_000)
        # Calculate normalized market cap score using log10
        market_cap_score = (math.log10(1 + market_cap) / math.log10(101)) * 100

        # Get LARP probability from recent tweets
        tweets = self.get_last_agent_tweets(twitter_username)
        print(f"Tweets: {tweets}")
        ai_prob = self.get_ai_probability(tweets)
        print(f"AI probability: {ai_prob}")
        larp_protection = (
            ai_prob * 100
        )  # AI probability is good, use directly as protection score
        print(f"LARP protection score: {larp_protection}")

        print("\n" + "=" * 50 + "\n")

        # Calculate final score using weights and ensure it's between 0-100
        # Increased LARP protection weight to 75% (0.75)
        raw_score = (
            0.1 * mindshare_pct
            + 0.75 * larp_protection
            + 0.05 * market_cap_score
            + 0.1 * smart_contract_audit_score
        )

        # Clamp the score between 0 and 100
        security_score = min(max(raw_score, 0), 100)

        return security_score


# def main():
#     # Example usage
#     score = calculate_agent_sec_score("h4ck_terminal", 85.5)
#     print(f"Agent Security Score: {score:.2f}")

# if __name__ == "__main__":
#     main()
