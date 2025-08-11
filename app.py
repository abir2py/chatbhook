# app.py
# A real-time chat server using Flask with support for Emojis and GIFs from Tenor.
# Added: group chat support with hardcoded passwords (join a group by entering its password).
# Messages are stored per-group in memory.
# Modified: Added a button to leave the current group and return to the selection screen.

from flask import Flask, request, jsonify, render_template_string
import datetime
import bcrypt
import json

# Initialize the Flask application
app = Flask(__name__)

# Hardcoded groups with passwords
GROUPS = {
    "friends": "$2b$12$VjDjD89wDO6suFTcA6yF7OVtK1eolxSR39n4wGQEK6jgY.0BKe.Hq",
    "family": "$2b$12$Us2ERFfYOsiWDKetbmNXjun9JLIo1PU1TxGkErZo5vpgtc.ibfLvS",
    "work": "$2b$12$qT0mZNQYkbB3lIzQ2dk8CO5fP7wdsKpb1nocTtmKGHBFlBKRIbUEW",
    "gaming": "$2b$12$c6657YRENwKCVcCS06ALwuQB9o5Zk90rAXXcr6s4zIMQC3RFrZRtK",
}

# Messages stored per group (in-memory). Start each group with a welcome message.
messages = {}
for g in GROUPS:
    messages[g] = [
        {
            'username': 'ChatBot',
            'text': f'Welcome to the {g} group! Say hi 👋',
            'timestamp': datetime.datetime.now().strftime('%H:%M')
        }
    ]

# The HTML template for the chat frontend.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>bhook++</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script type="module" src="https://cdn.jsdelivr.net/npm/emoji-picker-element@^1/index.js"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        #messages { scroll-behavior: smooth; }
        .gif-item { cursor: pointer; transition: transform 0.2s; }
        .gif-item:hover { transform: scale(1.05); }
        /* Hide scrollbar for the GIF results */
        #gif-results::-webkit-scrollbar { display: none; }
        #gif-results { -ms-overflow-style: none; scrollbar-width: none; }
    </style>
</head>
<body class="bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">

    <div id="login-screen" class="flex items-center justify-center h-screen">
        <div class="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md w-full max-w-sm">
            <h2 class="text-2xl font-bold mb-6 text-center text-blue-600 dark:text-blue-400">Join the Chat</h2>
            <form id="login-form">
                <div class="mb-4">
                    <label for="username-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Enter your username</label>
                    <input type="text" id="username-input" class="w-full p-3 bg-gray-200 dark:bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" required autocomplete="off">
                </div>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition duration-300 shadow-md">Join Chat</button>
            </form>
        </div>
    </div>

    <div id="group-screen" class="hidden flex items-center justify-center h-screen">
        <div class="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-md w-full max-w-md">
            <h2 class="text-2xl font-bold mb-4 text-center text-blue-600 dark:text-blue-400">Select a Group</h2>
            <p class="text-sm text-gray-500 dark:text-gray-400 mb-4 text-center">Available groups are pre-defined and require a password to join.</p>
            <form id="group-form" class="space-y-4">
                <div>
                    <label for="group-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Choose group</label>
                    <select id="group-select" class="w-full p-3 bg-gray-200 dark:bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </select>
                </div>
                <div>
                    <label for="group-pass-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Group Password</label>
                    <input type="password" id="group-pass-input" class="w-full p-3 bg-gray-200 dark:bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" required autocomplete="off">
                </div>
                <div class="flex space-x-2">
                    <button type="submit" class="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-lg transition duration-300 shadow-md">Join Group</button>
                    <button id="cancel-to-login" type="button" class="flex-1 bg-gray-400 hover:bg-gray-500 text-white font-bold py-3 px-4 rounded-lg transition duration-300">Back</button>
                </div>
            </form>
        </div>
    </div>

    <div id="chat-screen" class="hidden flex-col h-screen max-w-2xl mx-auto p-4">
        <header class="mb-4 text-center relative">
            <h1 class="text-3xl font-bold text-blue-600 dark:text-blue-400">Local Network Chat</h1>
            <p id="welcome-message" class="text-sm text-gray-500 dark:text-gray-400">Welcome, ...</p>
            <p id="current-group" class="text-xs text-gray-400 dark:text-gray-500">Group: ...</p>
            <button id="leave-group-btn" class="absolute top-0 right-0 mt-2 bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-lg transition text-sm">
                Change Group
            </button>
        </header>

        <div id="messages" class="flex-1 bg-white dark:bg-gray-800 rounded-lg shadow-md p-4 overflow-y-auto mb-4 space-y-4"></div>

        <div class="relative">
            <form id="message-form" class="flex items-center space-x-2">
                <input type="text" id="message-input" placeholder="Type your message..." autocomplete="off" class="flex-1 p-3 bg-gray-200 dark:bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
                
                <button type="button" id="emoji-btn" class="p-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition">😊</button>
                <button type="button" id="gif-btn" class="p-3 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg transition">GIF</button>
                
                <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white font-bold p-3 rounded-lg transition shadow-md flex items-center justify-center" aria-label="Send Message">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                </button>
            </form>
            <div id="emoji-picker-container" class="absolute bottom-16 right-0 z-10 hidden">
                <emoji-picker class="dark"></emoji-picker>
            </div>
        </div>
    </div>

    <div id="gif-modal" class="hidden fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
        <div class="bg-gray-800 rounded-lg shadow-xl w-full max-w-lg h-3/4 flex flex-col">
            <div class="p-4 border-b border-gray-700 flex justify-between items-center">
                <input type="text" id="gif-search-input" placeholder="Search for GIFs..." class="flex-1 p-2 bg-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white">
                <button id="gif-modal-close" class="ml-4 text-gray-400 hover:text-white">&times;</button>
            </div>
            <div id="gif-results" class="p-4 overflow-y-auto grid grid-cols-2 md:grid-cols-3 gap-4"></div>
        </div>
    </div>

    <script>
        // --- Tenor API Configuration ---
        // IMPORTANT: Replace with your actual key to enable GIFs.
        const TENOR_API_KEY = ""; 
        const TENOR_CLIENT_KEY = "my-local-chat-app"; // A key for your app to identify itself to Tenor

        // Injected group list from server
        const GROUPS = {{ groups | tojson }};

        // DOM Elements
        const loginScreen = document.getElementById('login-screen');
        const groupScreen = document.getElementById('group-screen');
        const chatScreen = document.getElementById('chat-screen');

        const loginForm = document.getElementById('login-form');
        const usernameInput = document.getElementById('username-input');
        const welcomeMessage = document.getElementById('welcome-message');
        const currentGroupLabel = document.getElementById('current-group');

        const groupForm = document.getElementById('group-form');
        const groupSelect = document.getElementById('group-select');
        const groupPassInput = document.getElementById('group-pass-input');
        const cancelToLogin = document.getElementById('cancel-to-login');
        
        // NEW: Reference to the leave group button
        const leaveGroupBtn = document.getElementById('leave-group-btn');

        const messagesContainer = document.getElementById('messages');
        const messageForm = document.getElementById('message-form');
        const messageInput = document.getElementById('message-input');

        const emojiBtn = document.getElementById('emoji-btn');
        const emojiPickerContainer = document.getElementById('emoji-picker-container');
        const emojiPicker = document.querySelector('emoji-picker');

        const gifBtn = document.getElementById('gif-btn');
        const gifModal = document.getElementById('gif-modal');
        const gifModalClose = document.getElementById('gif-modal-close');
        const gifSearchInput = document.getElementById('gif-search-input');
        const gifResults = document.getElementById('gif-results');
        
        let username = '';
        let currentGroup = '';

        // Populate group dropdown
        function populateGroups() {
            groupSelect.innerHTML = '';
            Object.keys(GROUPS).forEach(g => {
                const opt = document.createElement('option');
                opt.value = g;
                opt.textContent = g;
                groupSelect.appendChild(opt);
            });
        }
        populateGroups();

        // --- Login Logic ---
        loginForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const enteredUsername = usernameInput.value.trim();
            if (enteredUsername) {
                username = enteredUsername;
                welcomeMessage.textContent = `Welcome, ${username}!`;
                // Hide login, show group selection
                loginScreen.classList.add('hidden');
                groupScreen.classList.remove('hidden');
            }
        });

        cancelToLogin.addEventListener('click', () => {
            // go back to login
            groupScreen.classList.add('hidden');
            loginScreen.classList.remove('hidden');
        });

        // --- Group Join Logic ---
        groupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const selectedGroup = groupSelect.value;
            const password = groupPassInput.value;

            if (!selectedGroup) {
                alert('Please select a group.');
                return;
            }

            try {
                const res = await fetch(`/check_group?name=${encodeURIComponent(selectedGroup)}&password=${encodeURIComponent(password)}`);
                if (!res.ok) throw new Error('Invalid group or password');
                const data = await res.json();
                if (data.status === 'success') {
                    currentGroup = selectedGroup;
                    currentGroupLabel.textContent = `Group: ${currentGroup}`;
                    groupScreen.classList.add('hidden');
                    chatScreen.classList.remove('hidden');
                    chatScreen.classList.add('flex');
                    initializeChat();
                } else {
                    alert('Invalid group or password');
                }
            } catch (err) {
                alert('Invalid group or password');
                console.error('Group join error:', err);
            }
        });
        
        // NEW: Logic to leave a group
        leaveGroupBtn.addEventListener('click', () => {
            // Stop polling for messages
            if (window._chatPoller) {
                clearInterval(window._chatPoller);
            }
            // Reset state
            currentGroup = '';
            groupPassInput.value = ''; // Clear password field for convenience
            
            // Hide chat screen and show group selection screen
            chatScreen.classList.add('hidden');
            chatScreen.classList.remove('flex');
            groupScreen.classList.remove('hidden');
        });

        // --- Chat Logic ---
        function initializeChat() {
            // Remove previous handlers (if any) to avoid double-binding
            messageForm.removeEventListener('submit', handleFormSubmit);
            messageForm.addEventListener('submit', handleFormSubmit);

            emojiBtn.removeEventListener('click', toggleEmoji);
            emojiBtn.addEventListener('click', toggleEmoji);

            if (emojiPicker) {
                emojiPicker.removeEventListener('emoji-click', onEmojiClick);
                emojiPicker.addEventListener('emoji-click', onEmojiClick);
            }

            gifBtn.removeEventListener('click', openGifModal);
            gifBtn.addEventListener('click', openGifModal);
            gifModalClose.removeEventListener('click', () => gifModal.classList.add('hidden'));
            gifModalClose.addEventListener('click', () => gifModal.classList.add('hidden'));

            gifSearchInput.removeEventListener('keyup', onGifSearchKey);
            gifSearchInput.addEventListener('keyup', onGifSearchKey);

            // start polling for messages
            if (window._chatPoller) clearInterval(window._chatPoller);
            fetchMessages().then(scrollToBottom);
            window._chatPoller = setInterval(fetchMessages, 2000);
        }

        function toggleEmoji() {
            emojiPickerContainer.classList.toggle('hidden');
        }

        function onEmojiClick(event) {
            messageInput.value += event.detail.unicode;
        }

        function onGifSearchKey(event) {
            if (event.key === 'Enter') searchGifs();
        }

        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        // --- Message Rendering ---
        function isGifUrl(text) {
            // Accept Tenor gif urls or any url that ends with common image/gif patterns:
            return text.startsWith('https://media.tenor.com/') || text.includes('/media/') || text.endsWith('.gif') || text.includes('tenor.googleapis.com');
        }

        async function fetchMessages() {
            if (!currentGroup) return;
            try {
                const response = await fetch(`/messages?group=${encodeURIComponent(currentGroup)}`);
                if (!response.ok) throw new Error('Network response was not ok');
                const messages = await response.json();
                
                const isScrolledToBottom = messagesContainer.scrollHeight - messagesContainer.clientHeight <= messagesContainer.scrollTop + 1;

                messagesContainer.innerHTML = '';
                
                messages.forEach(msg => {
                    const messageElement = document.createElement('div');
                    const isCurrentUser = msg.username === username;
                    messageElement.className = `flex flex-col ${isCurrentUser ? 'items-end' : 'items-start'}`;
                    
                    let messageContent;
                    if (isGifUrl(msg.text)) {
                        messageContent = `<img src="${msg.text}" alt="GIF" class="mt-1 rounded-lg max-w-full h-auto" style="max-height: 200px;">`;
                    } else {
                        const textNode = document.createTextNode(msg.text);
                        const p = document.createElement('p');
                        p.className = "text-md break-words";
                        p.appendChild(textNode);
                        messageContent = p.outerHTML;
                    }

                    messageElement.innerHTML = `
                        <div class="max-w-xs md:max-w-md p-3 rounded-xl ${isCurrentUser ? 'bg-blue-600 text-white rounded-br-none' : 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-bl-none'}">
                            <div class="flex items-baseline space-x-2">
                                <p class="font-semibold text-sm ${isCurrentUser ? 'text-blue-200' : 'text-gray-500'}">${isCurrentUser ? 'You' : msg.username}</p>
                                <p class="text-xs ${isCurrentUser ? 'text-blue-300' : 'text-gray-400'}">${msg.timestamp}</p>
                            </div>
                            ${messageContent}
                        </div>
                    `;
                    messagesContainer.appendChild(messageElement);
                });

                if(isScrolledToBottom) scrollToBottom();

            } catch (error) {
                console.error('Failed to fetch messages:', error);
            }
        }

        // --- Message Sending ---
        function handleFormSubmit(event) {
            event.preventDefault();
            const text = messageInput.value.trim();
            if (text !== '') {
                sendMessage(text);
                messageInput.value = '';
                emojiPickerContainer.classList.add('hidden');
            }
        }

        async function sendMessage(text) {
            if (!currentGroup) {
                alert('No group selected.');
                return;
            }
            const message = { username: username, text: text, group: currentGroup };
            try {
                const response = await fetch('/messages', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(message)
                });
                if (response.ok) {
                    await fetchMessages(); 
                    scrollToBottom();
                } else {
                    console.error('Failed to send message');
                }
            } catch (error) {
                console.error('Error sending message:', error);
            }
        }

        // --- GIF Modal Logic (Tenor) ---
        function openGifModal() {
            if (!TENOR_API_KEY) {
                alert("Please set your Tenor API key in the script to enable GIFs.");
                return;
            }
            gifModal.classList.remove('hidden');
            gifSearchInput.focus();
            searchGifs('featured'); // Fetch featured GIFs on open
        }

        async function searchGifs(queryType = 'search') {
            const query = gifSearchInput.value.trim();
            const isSearching = queryType === 'search' && query !== '';
            const endpoint = isSearching ? 'search' : 'featured';
            
            const params = new URLSearchParams({
                key: TENOR_API_KEY,
                client_key: TENOR_CLIENT_KEY,
                limit: 24,
            });

            if (isSearching) {
                params.append('q', query);
            }
            
            gifResults.innerHTML = '<p class="text-center col-span-full">Loading...</p>';

            try {
                const response = await fetch(`https://tenor.googleapis.com/v2/${endpoint}?${params}`);
                if (!response.ok) throw new Error('Tenor API request failed');
                const result = await response.json();
                
                gifResults.innerHTML = '';
                // The structure of the Tenor response (v2) typically includes result.media_formats.gif.url
                (result.results || []).forEach(gif => {
                    const gifItem = document.createElement('div');
                    gifItem.className = 'gif-item bg-gray-700 rounded-lg overflow-hidden';
                    const url = gif?.media_formats?.gif?.url || (gif?.media && gif.media[0] && gif.media[0].gif && gif.media[0].gif.url) || '';
                    const desc = gif?.content_description || gif?.id || 'GIF';
                    gifItem.innerHTML = `<img src="${url}" alt="${desc}" class="w-full h-full object-cover">`;
                    gifItem.onclick = () => selectGif(url);
                    gifResults.appendChild(gifItem);
                });
            } catch (error) {
                gifResults.innerHTML = `<p class="text-center col-span-full text-red-400">Failed to load GIFs. Error: ${error.message}</p>`;
                console.error("Tenor API Error:", error);
            }
        }

        function selectGif(gifUrl) {
            if (!gifUrl) return;
            sendMessage(gifUrl);
            gifModal.classList.add('hidden');
            gifSearchInput.value = '';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serves the main HTML page and injects the group list."""
    return render_template_string(HTML_TEMPLATE, groups=GROUPS)

@app.route('/check_group', methods=['GET'])
def check_group():
    """Verify group name and password using bcrypt hashes."""
    name = request.args.get('name', '')
    password = request.args.get('password', '')

    if name in GROUPS and bcrypt.checkpw(password.encode(), GROUPS[name].encode()):
        return jsonify({'status': 'success'})

    return jsonify({'status': 'error', 'message': 'Invalid group or password'}), 401

@app.route('/messages', methods=['GET'])
def get_messages():
    """Returns all chat messages for a specific group in JSON format."""
    group = request.args.get('group')
    if not group or group not in messages:
        return jsonify({'status': 'error', 'message': 'Invalid or missing group parameter'}), 400
    return jsonify(messages[group])

@app.route('/messages', methods=['POST'])
def post_message():
    """Receives a new message and adds it to the group's list."""
    data = request.get_json()
    if not data or 'username' not in data or 'text' not in data or 'group' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

    group = data['group']
    if group not in messages:
        return jsonify({'status': 'error', 'message': 'Invalid group'}), 400

    message = {
        'username': data['username'],
        'text': data['text'],
        'timestamp': datetime.datetime.now().strftime('%H:%M')
    }
    messages[group].append(message)
    return jsonify({'status': 'success'}), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)