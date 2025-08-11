# app.py
# A real-time chat server using Flask with support for Emojis, GIFs, and ephemeral image uploads.
# - Group chat support with hardcoded passwords.
# - Option to go back to group selection.
# - Image sharing via Base64 encoding (images are stored in memory and disappear on restart).

from flask import Flask, request, jsonify, render_template_string
import datetime
import bcrypt
import json
import base64 # <-- Required for image encoding

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
                
                <label for="image-upload" class="p-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition cursor-pointer" aria-label="Upload Image">
                    🖼️
                    <input type="file" id="image-upload" class="hidden" accept="image/*">
                </label>
                
                <button type="button" id="emoji-btn" class="p-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition">😊</button>
                <button type="button" id="gif-btn" class="p-3 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg transition">GIF</button>
                
                <button type="submit" class="bg-blue-600 hover:bg-blue-700 text-white font-bold p-3 rounded-lg transition shadow-md flex items-center justify-center" aria-label="Send Message">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                </button>
            </form>
            <div id="image-preview-container" class="hidden mt-2 p-2 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center space-x-2">
                <img id="image-preview" class="max-h-20 rounded" src="">
                <button id="cancel-image" class="text-red-500 hover:text-red-700 font-bold">&times;</button>
            </div>
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
        const TENOR_API_KEY = ""; 
        const TENOR_CLIENT_KEY = "my-local-chat-app"; 

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
        
        // --- NEW: Image upload elements ---
        const imageUpload = document.getElementById('image-upload');
        const imagePreviewContainer = document.getElementById('image-preview-container');
        const imagePreview = document.getElementById('image-preview');
        const cancelImage = document.getElementById('cancel-image');
        let selectedFile = null;

        let username = '';
        let currentGroup = '';

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

        // --- Event Listeners ---
        loginForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const enteredUsername = usernameInput.value.trim();
            if (enteredUsername) {
                username = enteredUsername;
                welcomeMessage.textContent = `Welcome, ${username}!`;
                loginScreen.classList.add('hidden');
                groupScreen.classList.remove('hidden');
            }
        });

        cancelToLogin.addEventListener('click', () => {
            groupScreen.classList.add('hidden');
            loginScreen.classList.remove('hidden');
        });

        leaveGroupBtn.addEventListener('click', () => {
            if (window._chatPoller) clearInterval(window._chatPoller);
            currentGroup = '';
            groupPassInput.value = '';
            chatScreen.classList.add('hidden');
            chatScreen.classList.remove('flex');
            groupScreen.classList.remove('hidden');
        });

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
        
        // --- NEW: Image handling event listeners ---
        imageUpload.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                selectedFile = file;
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.classList.remove('hidden');
                    messageInput.placeholder = "Image selected. Press send.";
                    messageInput.disabled = true; 
                };
                reader.readAsDataURL(file);
            }
        });

        cancelImage.addEventListener('click', () => {
            selectedFile = null;
            imageUpload.value = ''; // Clear the file input
            imagePreviewContainer.classList.add('hidden');
            messageInput.placeholder = "Type your message...";
            messageInput.disabled = false;
        });


        // --- Chat Logic ---
        function initializeChat() {
            messageForm.onsubmit = handleFormSubmit;
            emojiBtn.onclick = toggleEmoji;
            if (emojiPicker) emojiPicker.addEventListener('emoji-click', onEmojiClick);
            gifBtn.onclick = openGifModal;
            gifModalClose.onclick = () => gifModal.classList.add('hidden');
            gifSearchInput.onkeyup = onGifSearchKey;
            
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
        function isMediaUrl(text) {
            return text.startsWith('data:image') || text.startsWith('https://media.tenor.com/') || text.includes('/media/') || text.endsWith('.gif') || text.includes('tenor.googleapis.com');
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
                    if (isMediaUrl(msg.text)) {
                        messageContent = `<img src="${msg.text}" alt="Chat content" class="mt-1 rounded-lg max-w-full h-auto" style="max-height: 250px;">`;
                    } else {
                        const p = document.createElement('p');
                        p.className = "text-md break-words";
                        p.textContent = msg.text;
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

        // --- Message & Image Sending ---
        async function handleFormSubmit(event) {
            event.preventDefault();
            emojiPickerContainer.classList.add('hidden');

            if (selectedFile) {
                await sendImage(selectedFile);
                // Reset after sending
                cancelImage.click(); // Programmatically click cancel to reset UI
            } else {
                const text = messageInput.value.trim();
                if (text !== '') {
                    sendMessage(text);
                    messageInput.value = '';
                }
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
        
        // NEW: Function to upload the image file
        async function sendImage(file) {
            const formData = new FormData();
            formData.append('image', file);
            formData.append('username', username);
            formData.append('group', currentGroup);

            try {
                const response = await fetch('/upload_image', {
                    method: 'POST',
                    body: formData
                });
                if (response.ok) {
                    await fetchMessages();
                    scrollToBottom();
                } else {
                    alert('Failed to upload image. Please try again.');
                    console.error('Failed to send image');
                }
            } catch (error) {
                console.error('Error sending image:', error);
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
            searchGifs('featured');
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
            if (isSearching) params.append('q', query);
            
            gifResults.innerHTML = '<p class="text-center col-span-full">Loading...</p>';

            try {
                const response = await fetch(`https://tenor.googleapis.com/v2/${endpoint}?${params}`);
                if (!response.ok) throw new Error('Tenor API request failed');
                const result = await response.json();
                
                gifResults.innerHTML = '';
                (result.results || []).forEach(gif => {
                    const gifItem = document.createElement('div');
                    gifItem.className = 'gif-item bg-gray-700 rounded-lg overflow-hidden';
                    const url = gif?.media_formats?.gif?.url || '';
                    const desc = gif?.content_description || 'GIF';
                    if (!url) return;
                    gifItem.innerHTML = `<img src="${url}" alt="${desc}" class="w-full h-full object-cover">`;
                    gifItem.onclick = () => selectGif(url);
                    gifResults.appendChild(gifItem);
                });
            } catch (error) {
                gifResults.innerHTML = `<p class="text-center col-span-full text-red-400">Failed to load GIFs: ${error.message}</p>`;
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
    """Receives a new text message and adds it to the group's list."""
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

# --- NEW: Route for handling image uploads ---
@app.route('/upload_image', methods=['POST'])
def upload_image():
    """Receives an uploaded image, encodes it to base64, and adds it as a message."""
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image part'}), 400

    file = request.files['image']
    username = request.form.get('username')
    group = request.form.get('group')

    if not all([file, username, group]):
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
        
    if group not in messages:
        return jsonify({'status': 'error', 'message': 'Invalid group'}), 400

    # Encode the image to a base64 data URL
    try:
        encoded_string = base64.b64encode(file.read()).decode('utf-8')
        mime_type = file.content_type
        image_data_url = f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Could not process file: {e}'}), 500


    message = {
        'username': username,
        'text': image_data_url,  # The text is now the image data URL
        'timestamp': datetime.datetime.now().strftime('%H:%M')
    }
    messages[group].append(message)
    return jsonify({'status': 'success'}), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)