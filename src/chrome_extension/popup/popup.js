
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  if (!tab.url.includes('...')) {
    window.close();
  }
});

document.addEventListener("DOMContentLoaded", function () {
    // Your code here

    chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: () => {
            return {
                server: localStorage.getItem('...'),
                secret: localStorage.getItem('...')
            }
        }
    }, (results) => {
        const data = results?.[0]?.result;
        document.getElementById('server').value = data?.server
        document.getElementById('secret').value = data?.secret
    });
    });

    
    document.querySelector('form').onsubmit = save
});


async function save(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (d) => {
            localStorage.setItem('...', d.server);
            localStorage.setItem('...', d.secret);
        },
        args: [data]
    });

    window.close();
}