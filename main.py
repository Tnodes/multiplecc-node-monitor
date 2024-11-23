import requests
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import telebot
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
ALLOWED_CHAT_ID = int(os.getenv('CHAT_ID', 0))

# Store previous bot messages
previous_messages = []

@dataclass
class UserInformation:
    wallet_addr: str
    unique_identification_code: str
    email: str
    nickname: str
    avatar_url: str
    email_verification_status: int

@dataclass
class NodeStatus:
    node_status: int
    nodes_total_running_time: int

    def get_time_breakdown(self) -> tuple[int, int, int]:
        hours, remainder = divmod(self.nodes_total_running_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        return hours, minutes, seconds

class MultipleAPIClient:
    BASE_URL = "https://api.app.multiple.cc"
    
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.headers = {
            "accept": "application/json",
            "authorization": f"Bearer {auth_token}",
            "origin": "https://www.app.multiple.cc",
            "referer": "https://www.app.multiple.cc/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def get_user_information(self) -> Optional[UserInformation]:
        try:
            response = requests.get(
                f"{self.BASE_URL}/User/GetInformation",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get("success"):
                print(f"API Error: {data.get('errorMessage')}")
                return None
                
            user_data = data["data"]
            return UserInformation(
                wallet_addr=user_data["walletAddr"],
                unique_identification_code=user_data["uniqueIdentificationCode"],
                email=user_data["email"],
                nickname=user_data["nickname"],
                avatar_url=user_data["avatarUrl"],
                email_verification_status=user_data["emailVerificationStatus"]
            )
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            return None
        except json.JSONDecodeError:
            print("Failed to parse JSON response")
            return None
        except KeyError as e:
            print(f"Missing expected data in response: {str(e)}")
            return None

    def get_node_running_status(self) -> Optional[NodeStatus]:
        try:
            response = requests.get(
                f"{self.BASE_URL}/User/GetNodeRunningStatus",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get("success"):
                print(f"API Error: {data.get('errorMessage')}")
                return None
                
            status_data = data["data"]
            return NodeStatus(
                node_status=status_data["nodeStatus"],
                nodes_total_running_time=status_data["nodesTotalRunningTime"]
            )
            
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            return None
        except json.JSONDecodeError:
            print("Failed to parse JSON response")
            return None
        except KeyError as e:
            print(f"Missing expected data in response: {str(e)}")
            return None

def read_tokens(filename: str = "token.txt") -> List[str]:
    try:
        with open(filename, 'r') as file:
            tokens = [line.strip() for line in file.readlines() if line.strip()]
        return tokens
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return []
    except Exception as e:
        print(f"Error reading tokens: {str(e)}")
        return []

def format_account_info(token: str) -> str:
    client = MultipleAPIClient(token)
    message_parts = []
    
    # Get user information
    user_info = client.get_user_information()
    if user_info:
        message_parts.extend([
            "📱 User Information:",
            f"👛 Wallet: {user_info.wallet_addr[:6]}...{user_info.wallet_addr[-4:]}",
            f"🆔 ID: {'*' * len(user_info.unique_identification_code)}",
            f"👤 Nickname: {user_info.nickname}",
        ])
    
    # Get node running status
    node_status = client.get_node_running_status()
    if node_status:
        hours, minutes, seconds = node_status.get_time_breakdown()
        status_emoji = "🟢" if node_status.node_status == 1 else "🔴"
        
        message_parts.extend([
            "\n⚙️ Node Status:",
            f"{status_emoji} Status: {'Running' if node_status.node_status == 1 else 'Stopped'}",
            f"⏱ Running Time: {hours}h {minutes}m {seconds}s",
        ])
    
    return "\n".join(message_parts)

def setup_telegram_bot():
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    return telebot.TeleBot(bot_token)

def is_authorized(message) -> bool:
    incoming_chat_id = message.chat.id
    print(f"Incoming chat ID: {incoming_chat_id}")
    print(f"Allowed chat ID: {ALLOWED_CHAT_ID}")
    print(f"Types - Incoming: {type(incoming_chat_id)}, Allowed: {type(ALLOWED_CHAT_ID)}")
    return str(incoming_chat_id) == str(ALLOWED_CHAT_ID)

def delete_previous_messages(bot, chat_id):
    """
    Delete all previous bot messages
    """
    global previous_messages
    for message_id in previous_messages:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception as e:
            print(f"Failed to delete message {message_id}: {str(e)}")
    previous_messages.clear()

def send_message(bot, chat_id, text):
    """
    Send message and store its ID
    """
    global previous_messages
    message = bot.send_message(chat_id, text)
    previous_messages.append(message.message_id)
    return message

def reply_and_store(bot, message, text):
    """
    Reply to message and store the bot's response message ID
    """
    global previous_messages
    response = bot.reply_to(message, text)
    previous_messages.append(response.message_id)
    return response

def main():
    print("Environment Check:")
    print(f"CHAT_ID from env: {os.getenv('CHAT_ID')}")
    print(f"Converted CHAT_ID: {ALLOWED_CHAT_ID}")
    
    bot = setup_telegram_bot()
    
    @bot.message_handler(commands=['start', 'help', 'info'])
    def handle_command(message):
        if not is_authorized(message):
            bot.reply_to(message, "⛔ Unauthorized access")
            return
            
        # Delete previous messages
        delete_previous_messages(bot, message.chat.id)
        
        command = message.text.split('@')[0]  # Remove bot username from command if present
        
        if command == '/start':
            welcome_text = (
                "👋 Welcome to Multiple.cc Node Monitor!\n\n"
                "Available commands:\n"
                "/info - Check node status and information\n"
                "/help - Show this help message"
            )
            reply_and_store(bot, message, welcome_text)
            
        elif command == '/help':
            help_text = (
                "📚 Available Commands:\n\n"
                "/info - Display information for all registered nodes\n"
                "/help - Show this help message"
            )
            reply_and_store(bot, message, help_text)
            
        elif command == '/info':
            try:
                tokens = read_tokens()
                if not tokens:
                    reply_and_store(bot, message, "❌ No tokens found. Please add tokens to token.txt")
                    return
                
                initial_msg = reply_and_store(bot, message, f"📊 Found {len(tokens)} accounts. Fetching information...")
                
                for index, token in enumerate(tokens, 1):
                    account_info = format_account_info(token)
                    header = f"🔷 Account #{index}\n{'='*20}\n"
                    reply_and_store(bot, message, f"{header}{account_info}")
                
            except Exception as e:
                reply_and_store(bot, message, f"❌ Error occurred: {str(e)}")
    
    print("Telegram bot started...")
    print(f"Authorized Chat ID: {ALLOWED_CHAT_ID}")
    bot.infinity_polling()

if __name__ == "__main__":
    main()
