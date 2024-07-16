class Chatbox {
    constructor() {
        this.args = {
            chatBox: document.querySelector('.chatbox__support'),
            sendButton: document.querySelector('.send__button'),
            imageButton: document.querySelector('.image__button'), 
            fileInput: document.querySelector('.file-input'),
        }

        this.state = true; // Set the state to true to initially display the chatbox
        this.messages = [];
    }

    display() {
        const { chatBox, sendButton} = this.args;
        sendButton.addEventListener('click', () => this.onSendButton(chatBox));

        const node = chatBox.querySelector('.text_input');

        node.addEventListener("keyup", ({ key }) => {
            event.preventDefault();  // Prevent the form from causing a page refresh
            
            if (key === "Enter") {
                this.onSendButton(chatBox);
            }
        });
        
        // Initially display the chatbox
        chatBox.classList.add('chatbox--active');
        
        const description = [
            "Hello! My name is REMONI. I am your virtual nurse.",
            "How can I help you?"
        ];

        let index = 0;
        const displayNextMessage = () => {
            if (index < description.length) {
                this.messages.push({ name: "REMONI", message: description[index] });
                this.updateChatText(chatBox);
                index++;
                setTimeout(displayNextMessage, 1500); // 1000 milliseconds (1 second) delay
            }
        };
        displayNextMessage();
        
        // Connect to the WebSocket server
        const socket = io();

        // Listen for the fall_alert event
        socket.on('fall_alert', (data) => {
            //alert(data.message); // Show an alert with the message
            // Or you can update the chatbox with the message
            console.log(data.message)
            this.messages.push({ name: "REMONI", message: "The system has detected a health emergency. A notification has already been sent to your caregiver." });
            this.updateChatText(chatBox);
        });
    }

    onSendButton(chatbox) {
        var textField = chatbox.querySelector('.text_input');
        let text1 = textField.value
        if (text1 === "") {
            return;
        }

        let msg1 = { name: "User", message: text1 }
        this.messages.push(msg1);
        this.updateChatText(chatbox);
        textField.value = '';
        //'http://127.0.0.1:5000/doctor/chat'
        fetch($SCRIPT_ROOT + '/chat_patient', {
            method: 'POST',
            body: JSON.stringify({ message: text1 }),
            mode: 'cors',
            headers: {
              'Content-Type': 'application/json'
            },
          })
          .then(r => r.json())
          .then(r => {
            console.log(r)
            let msg2 = { name: "REMONI", message: r.answer };
            this.messages.push(msg2);
            this.updateChatText(chatbox);
            textField.value = '';
            if ('show_list' in r){
                console.log('showing image');
                r.show_list.forEach(file_path => {
                    // Push an object with the name "Image" and the file path to this.messages
                    this.messages.push({ name: "REMONI_Image", message: file_path });
                    console.log(file_path);
                    this.updateChatText(chatbox);
                });
            }
            }).catch((error) => {
            let msg2 = { name: "REMONI", message: "Sorry, the system is currently experiencing an error. Please try again later." };
            this.messages.push(msg2);
            console.error('Error:', error);
            this.updateChatText(chatbox);
            textField.value = ''
          });
          
    }
    

    updateChatText(chatbox) {
        var html = '';
        this.messages.slice().reverse().forEach(function(item, index) {
            if (item.name === "REMONI")
            {
                html += '<div class="messages__item messages__item--visitor">' + item.message + '</div>'
            }
            else if (item.name === "REMONI_Image")
            {
                html += '<image src="' + item.message + '" class="messages__item messages__item--image--operator">'
            
            }
            else
            {
                html += '<div class="messages__item messages__item--operator">' + item.message + '</div>'
            }
          });

        const chatmessage = chatbox.querySelector('.chatbox__messages');
        chatmessage.innerHTML = html;
        const isScrolledToBottom = chatmessage.scrollHeight - chatmessage.clientHeight <= chatmessage.scrollTop + 1;
        if (isScrolledToBottom) {
        chatmessage.scrollTop = chatmessage.scrollHeight;
        }
    }
}

const chatbox = new Chatbox();
chatbox.display();
