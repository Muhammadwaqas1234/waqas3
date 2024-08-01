$(document).ready(function() {
    const $userInput = $('#user-input');
    const $voiceButton = $('#voice-command-button');
    const $sendButton = $('#send-button');
    const $chatMessages = $('#chat-messages');
    const documentSessionContainer = document.getElementById('document-session-container');
    const $chatContainer = $('.chat-container');

     
     $('#user-input').click(function() {
        
        if ($('body').hasClass('sidebar-opened')) {
            $('body').removeClass('sidebar-opened');
            $('#open-sidebar-btn').show();
            $('.close-sidebar-btn').hide();
            adjustInputWidth(); 
        }
    });
    function clearChatHistory() {
        $('#chat-messages').empty(); 
        localStorage.removeItem('chatHistory'); 
    }
    
    
    $('#clear-history-btn').click(function() {
        clearChatHistory(); 
    });

    function handleAdditionalQuestionClick(question) {
        $userInput.val(question);
        sendMessage();
    }
    function appendAdditionalQuestion(question) {
    const additionalQuestionElement = $('<div class="additional-question"></div>').text(question);
    additionalQuestionElement.on('click', function() {
        $userInput.val(question);
        sendMessage();
    });
    $chatMessages.append(additionalQuestionElement);
    
    
}
   


    
    function handleResponse(response) {
        const { response_text, additional_questions, audio_data, document_session } = response;

         
         appendMessage('assistant', response_text, 'response');
          
    if (audio_data) {
        
        const audioElement = document.createElement('audio');
        audioElement.setAttribute('controls', ''); // Add controls for playback
        audioElement.src = 'data:audio/wav;base64,' + audio_data; // Set audio source
        audioElement.style.display = 'none'; // Hide the audio player initially

        // Create a button to trigger audio playback
        const audioButton = document.createElement('button');
        audioButton.id = 'listen-btn'; // Set button id for styling

        // Create an image element for the button
        const audioImage = document.createElement('img');
        audioImage.src = '/static/img/WhatsApp Image 2024-05-22 at 02.14.16_6f498517.jpg'; // Set path to your image
        audioImage.alt = 'Listen to Audio'; // Set alt text for accessibility
        audioImage.style.width = '38px'; // Apply width style
        audioImage.style.height = '30px'; // Apply height style
        audioImage.style.marginRight = '0px'; // Apply margin-right style
        let isPlaying = false; // Track whether audio is currently playing
        audioButton.appendChild(audioImage); // Append the image to the button
        audioButton.addEventListener('click', function() {
            if (!isPlaying) {
                audioElement.play(); // Start audio playback
                audioImage.src = '/static/img/WhatsApp Image 2024-05-22 at 02.14.16_6f498517.jpg'; // Change image to "Pause the Audio"
                audioImage.alt = 'Pause the Audio'; // Change alt text
                isPlaying = true; // Set isPlaying to true
            } else {
                audioElement.pause(); // Pause audio playback
                audioImage.src = '/static/img/WhatsApp Image 2024-05-22 at 02.14.16_6f498517.jpg'; // Change image back to "Listen to Audio"
                audioImage.alt = 'Listen to Audio'; // Change alt text
                isPlaying = false; // Set isPlaying to false
            }
        });



        // Append the audio button and audio element to the chat interface
        $chatMessages.append(audioButton);
        $chatMessages.append(audioElement);
        scrollChatContainerToBottom();
    }
    
   
    
        
       if (additional_questions && additional_questions.length > 0) {
            additional_questions.forEach((question) => {
                appendAdditionalQuestion(question);
            });
        }


 // Create a button element
const button = document.createElement('button');
button.innerHTML = '<img src="/static/img/png-transparent-computer-icons-book-book-cover-angle-recycling-logo-thumbnail-removebg-preview.png" alt="Reference" style="width:30px;height: 30px;">';

// Variable to keep track of the document session display state
let isDocumentSessionVisible = false;
let documentSessionElement = null;

button.addEventListener('click', function() {
    if (isDocumentSessionVisible) {
        // Hide the document session content
        if (documentSessionElement) {
            documentSessionElement.remove();
            documentSessionElement = null;
        }
    } else {
        // Display the document session content in the response area
        if (document_session) {
            documentSessionElement = document.createElement('div');
            documentSessionElement.classList.add('response');
            documentSessionElement.textContent = document_session;
            $chatMessages.append(documentSessionElement);
        }
    }
    // Toggle the document session display state
    isDocumentSessionVisible = !isDocumentSessionVisible;
});

// Apply CSS styles to the button
button.style.background = 'none';
button.style.border = 'none';
button.style.padding = '0';
button.style.cursor = 'pointer';

// Append the button to the chat interface
$chatMessages.append(button);
 // Handle additional questions, document session, etc.


// Function to scroll chat container to bottom
function scrollChatContainerToBottom() {
    $chatContainer.scrollTop($chatContainer[0].scrollHeight);
}
    
    } 

    // Function to send user message to the backend and handle response
    function sendMessageToBackend(message) {
        // Show loading animation
    $('#loading-animation').show();
        $.ajax({
            type: 'POST',
            url: '/chat', // Backend endpoint URL
            contentType: 'application/json',
            data: JSON.stringify({ user_question: message }),
            success: function(response) {
                 // Hide loading animation
            $('#loading-animation').hide();
                handleResponse(response);
            },
            error: function(xhr, status, error) {
                console.error('Error sending message:', error);
                 // Hide loading animation in case of error
            $('#loading-animation').hide();
            }
        });
    }
    // Function to toggle between voice and send buttons based on input value
    function toggleButtons() {
        const inputValue = $userInput.val().trim();
        if (inputValue !== '') {
            $voiceButton.hide();
            $sendButton.show();
        } else {
            $voiceButton.show();
            $sendButton.hide();
        }
    }

    // Event listener for input change
    $userInput.on('input', function() {
        toggleButtons(); // Toggle buttons based on input value
    });

    // Event listener for form submission (send button)
    $('#chat-form').submit(function(event) {
        event.preventDefault();
        const userQuestion = $userInput.val().trim();
        if (userQuestion !== '') {
            appendMessage('user', userQuestion, 'user');
            sendMessageToBackend(userQuestion);
            $userInput.val('');
            toggleButtons(); // Toggle buttons after sending message
        }
    });

    // Function to save chat history in local storage
function saveChatHistory(role, message) {
    let chatHistory = JSON.parse(localStorage.getItem('chatHistory')) || [];
    chatHistory.push({ role, text: message });
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}


    // Function to append message to chat interface with specific message type
    function appendMessage(role, message, type) {
        let messageElement;
        if (type === 'user') {
            messageElement = `<div id="user-message" class="chat-message">${message}</div>`;
        } else if (type === 'response') {
            messageElement = `<div id="response-message" class="chat-message">${message}</div>`;
        } else if (type === 'additional_question') {
            messageElement = `<div id="additional-question" class="chat-message">${message}</div>`;
        } else {
            // Default message style
            messageElement = `<div class="chat-message">${message}</div>`;
        }

        $chatMessages.append(messageElement);
        saveChatHistory(role, message); // Save message to chat history
        // Scroll chat container to bottom
    scrollChatContainerToBottom();
    
    }
    // Function to scroll chat container to bottom
function scrollChatContainerToBottom() {
    $chatContainer.scrollTop($chatContainer[0].scrollHeight);
}
   
    // Voice command button click event
    $('#voice-command-button').click(function() {
        voiceCommand(); // Call the voiceCommand function
    });

    // Function for voice command
    function voiceCommand() {
        var recognition = new webkitSpeechRecognition();
        recognition.lang = 'en-US';
        recognition.onresult = function(event) {
            var transcript = event.results[0][0].transcript;
            $userInput.val(transcript);
            $('#input').submit(); // Submit the form after setting the input value
        };
        recognition.start();
    }
     // Function to show chat history
     function showChatHistory() {
            // Assuming this function displays chat history (not defined in the provided code)
        }

        // Function to start a new chat and refresh the page
        function newChat() {
            location.reload(); // Reload the page
        }
        
        

        // Open sidebar button click event
        $('#open-sidebar-btn').click(function() {
            $('body').addClass('sidebar-opened');
            $('#open-sidebar-btn').hide();
            $('.close-sidebar-btn').show();
            adjustInputWidth();
        });

        // Close sidebar button click event
        $('.close-sidebar-btn').click(function() {
            $('body').removeClass('sidebar-opened');
            $('#open-sidebar-btn').show();
            $('.close-sidebar-btn').hide();
            adjustInputWidth();
        });

        // Automatically close sidebar when the page loads
        $('body').removeClass('sidebar-opened');
        $('#open-sidebar-btn').show();
        $('.close-sidebar-btn').hide();
        adjustInputWidth(); // Assuming this function is defined elsewhere
    }); 
    document.addEventListener('DOMContentLoaded', () => {
    const settingsLink = document.getElementById('settings-link');
    const settingsPopup = document.getElementById('settings-popup');
    const closeButton = document.getElementById('close-button');

    settingsLink.addEventListener('click', (event) => {
        event.preventDefault();
        settingsPopup.style.display = 'flex';
    });

    closeButton.addEventListener('click', () => {
        settingsPopup.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target == settingsPopup) {
            settingsPopup.style.display = 'none';
        }
    });

    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.addEventListener('click', (event) => {
            event.preventDefault();
            document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.settings-section').forEach(section => section.classList.remove('active'));
            tab.classList.add('active');
            const sectionId = tab.id.replace('-tab', '-section');
            if (sectionId === 'contact-us-section') {
                loadContactUsPage();
            } else {
                document.getElementById(sectionId).classList.add('active');
            }
        });
    });

    document.getElementById('general-tab').click(); // Open the General tab by default

    function loadContactUsPage() {
        fetch('settingshtml/contact-us.html')
            .then(response => response.text())
            .then(html => {
                document.getElementById('help-section').innerHTML = html;
                const script = document.createElement('script');
                script.textContent = `
                    document.getElementById('contact-form').addEventListener('submit', function(event) {
                        event.preventDefault();
                        console.log('Form submitted');
                    });
                `;
                document.getElementById('help-section').appendChild(script);
            })
            .catch(error => console.error('Error loading Contact Us page:', error));
    }
});

function saveLanguagePreference() {
        const selectedLanguage = document.getElementById("language-select").value;
        fetch("/save_language", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ language: selectedLanguage })
        }).then(response => {
            if (response.ok) {
                console.log("Language preference saved.");
            } else {
                console.error("Failed to save language preference.");
            }
        });
    }
document.addEventListener('DOMContentLoaded', () => {
    const settingsPopup = document.getElementById('settings-popup');
    const profileButton = document.getElementById('profile-button');
    const closeButton = document.getElementById('close-button');
    const tabs = document.querySelectorAll('.settings-tab');
    const sections = document.querySelectorAll('.settings-section');
    const contactUsLink = document.getElementById('contact-us-link');
    const contactUsForm = document.getElementById('contact-us-form');
    const helpContent = document.getElementById('help-content');
    const backToHelp = document.getElementById('back-to-help');
    const faqLink = document.getElementById('faq-link');
    const faqContent = document.getElementById('faq-content');
    const backToHelpFromFaq = document.getElementById('back-to-help-from-faq');
    const faqQuestions = document.querySelectorAll('.faq-question');

    profileButton.addEventListener('click', () => {
        settingsPopup.style.display = 'block';
    });

    closeButton.addEventListener('click', () => {
        settingsPopup.style.display = 'none';
    });

    tabs.forEach(tab => {
        tab.addEventListener('click', (event) => {
            event.preventDefault();
            const targetSection = document.getElementById(tab.getAttribute('data-section'));

            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(section => section.style.display = 'none');

            tab.classList.add('active');
            targetSection.style.display = 'block';
        });
    });

    contactUsLink.addEventListener('click', (event) => {
        event.preventDefault();
        helpContent.style.display = 'none';
        contactUsForm.style.display = 'block';
    });

    backToHelp.addEventListener('click', (event) => {
        event.preventDefault();
        contactUsForm.style.display = 'none';
        helpContent.style.display = 'block';
    });

    faqLink.addEventListener('click', (event) => {
        event.preventDefault();
        helpContent.style.display = 'none';
        faqContent.style.display = 'block';
    });

    backToHelpFromFaq.addEventListener('click', (event) => {
        event.preventDefault();
        faqContent.style.display = 'none';
        helpContent.style.display = 'block';
    });

    faqQuestions.forEach(question => {
        question.addEventListener('click', () => {
            const answer = question.nextElementSibling;
            if (answer.style.display === 'none') {
                answer.style.display = 'block';
            } else {
                answer.style.display = 'none';
            }
        });
    });

    // Optional: close the popup if user clicks outside of it
    window.addEventListener('click', (event) => {
        if (event.target === settingsPopup) {
            settingsPopup.style.display = 'none';
        }
    });
});
document.getElementById('contact-form').addEventListener('submit', function(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    
    fetch('/send-email', {
        method: 'POST',
        body: formData
    }).then(response => {
        if (response.ok) {
            alert('Email sent successfully!');
        } else {
            alert('Error sending email.');
        }
    }).catch(error => {
        alert('Error sending email.');
    });
});
const subscriptionTab = document.getElementById('subscription-tab');
const subscriptionSection = document.getElementById('subscription-section');
const subscribeButton = document.getElementById('subscribe-button');
var stripe = Stripe('pk_live_51PDNsQGthr7AaSvULnZNACBai9axnSrVJ0CqAbhbwr0F7Xg8EYrmCevgQYLDTGymKowgatM29bzeofxK8I4IZAdg00K7TIkTDk');
subscriptionTab.addEventListener('click', (event) => {
    event.preventDefault();
    tabs.forEach(t => t.classList.remove('active'));
    sections.forEach(section => section.style.display = 'none');
    subscriptionTab.classList.add('active');
    subscriptionSection.style.display = 'block';
});

subscribeButton.addEventListener('click', () => {
    fetch('/subscribe', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    }).then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    }).then(data => {
        if (data.error) {
            console.error('Error:', data.error);
        } else {
            const checkoutSessionId = data.checkout_session_id;
            stripe.redirectToCheckout({ sessionId: checkoutSessionId });
        }
    }).catch(error => {
        console.error('Error:', error);
    });
});




const selectedFiles = new Set();

document.getElementById('attachments').addEventListener('change', function() {
    const fileList = this.files;
    const output = document.getElementById('file-list');
    const selectedFiles = new Set();

    // Loop through the selected files and add them to the set
    for (let i = 0; i < fileList.length; i++) {
        selectedFiles.add(fileList[i].name);
    }

    // Function to update the displayed list
    function updateFileList() {
        // Clear the output container
        output.innerHTML = '';

        // Display all unique file names
        selectedFiles.forEach(fileName => {
            const listItem = document.createElement('div');
            listItem.className = 'file-item';
            listItem.textContent = fileName;

            const removeButton = document.createElement('span');
            removeButton.className = 'remove-button';
            removeButton.innerHTML = '&times;';
            removeButton.addEventListener('click', function() {
                selectedFiles.delete(fileName);
                updateFileList();
            });

            listItem.appendChild(removeButton);
            output.appendChild(listItem);
        });
    }

    updateFileList();
});
