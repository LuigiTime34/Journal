document.addEventListener('DOMContentLoaded', function() {
    // --- THEME TOGGLE LOGIC ---
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const applyStoredTheme = () => {
        const storedTheme = localStorage.getItem('theme') || 'dark';
        if (storedTheme === 'light') {
            body.classList.add('light-theme');
            body.classList.remove('dark-theme');
        } else {
            body.classList.add('dark-theme');
            body.classList.remove('light-theme');
        }
    };
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isLight = body.classList.contains('light-theme');
            localStorage.setItem('theme', isLight ? 'dark' : 'light');
            applyStoredTheme();
        });
    }
    applyStoredTheme();

    // --- MEMORIES PAGE LOGIC (Unchanged) ---
    const memoriesContainer = document.getElementById('memories-container');
    if (memoriesContainer) {
        const saveBtn = document.getElementById('save-memories-btn');
        const statusEl = document.getElementById('memories-save-status');
        const userMemoriesTextarea = document.getElementById('user-memories-textarea');
        const aiMemoriesTextarea = document.getElementById('ai-memories-textarea');
        const forgottenList = document.getElementById('forgotten-memories-list');
        const searchInput = document.getElementById('memory-search-input');
        
        const fetchMemories = async () => {
            const response = await fetch('/api/memories');
            const data = await response.json();
            userMemoriesTextarea.value = data.user_memories;
            aiMemoriesTextarea.value = data.ai_memories;
            renderForgottenList(data.forgotten_memories);
        };
        const renderForgottenList = (memories) => {
            forgottenList.innerHTML = '';
            if (!memories || memories.length === 0) {
                const li = document.createElement('li');
                li.textContent = "No forgotten memories.";
                li.classList.add('empty-list-item');
                forgottenList.appendChild(li);
                return;
            }
            memories.forEach(mem => {
                const li = document.createElement('li');
                li.innerHTML = `<span>${mem}</span> <button class="btn-secondary reinstate-btn" data-memory="${mem}">Reinstate</button>`;
                forgottenList.appendChild(li);
            });
        };
        const saveMemories = async () => {
            statusEl.textContent = 'Saving...';
            statusEl.style.opacity = '1';
            await fetch('/api/memories', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_memories: userMemoriesTextarea.value, ai_memories: aiMemoriesTextarea.value }) });
            statusEl.textContent = 'Saved!';
            setTimeout(() => { statusEl.style.opacity = '0'; }, 2000);
        };
        const handleForgottenMemoryAction = async (e, action) => {
            if (!e.target.dataset.memory) return;
            await fetch(`/api/memories/${action}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ memory: e.target.dataset.memory }) });
            fetchMemories();
        };
        
        fetchMemories();
        forgottenList.addEventListener('click', e => { if (e.target.classList.contains('reinstate-btn')) { handleForgottenMemoryAction(e, 'reinstate'); } });
        saveBtn.addEventListener('click', saveMemories);
        
        const tabs = document.querySelectorAll('.tab-link');
        const tabContents = document.querySelectorAll('.tab-content');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                tabContents.forEach(c => c.classList.remove('active'));
                document.getElementById(tab.dataset.tab).classList.add('active');
            });
        });
    }
});

const canvas = document.getElementById('particle-canvas');
if (canvas) {
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    let particlesArray;

    // Mouse position
    const mouse = {
        x: null,
        y: null,
        radius: (canvas.height / 100) * (canvas.width / 100) // Radius around mouse
    };

    window.addEventListener('mousemove', function(event) {
        mouse.x = event.x;
        mouse.y = event.y;
    });

    class Particle {
        constructor(x, y, directionX, directionY, size) {
            this.x = x; this.y = y; this.directionX = directionX; this.directionY = directionY; this.size = size;
        }
        // Draw individual particle
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2, false);
            const isLightTheme = document.body.classList.contains('light-theme');
            ctx.fillStyle = isLightTheme ? 'rgba(98, 0, 238, 0.15)' : 'rgba(187, 134, 252, 0.15)';
            ctx.fill();
        }
        // Move particle and keep it within screen bounds
        update() {
            if (this.x > canvas.width || this.x < 0) { this.directionX = -this.directionX; }
            if (this.y > canvas.height || this.y < 0) { this.directionY = -this.directionY; }
            this.x += this.directionX;
            this.y += this.directionY;
            this.draw();
        }
    }

    // Create particle array
    function init() {
        particlesArray = [];
        // A good density that scales with screen size
        let numberOfParticles = (canvas.height * canvas.width) / 10000;
        for (let i = 0; i < numberOfParticles; i++) {
            let size = (Math.random() * 2) + 1;
            let x = (Math.random() * ((innerWidth - size * 2) - (size * 2)) + size * 2);
            let y = (Math.random() * ((innerHeight - size * 2) - (size * 2)) + size * 2);
            let directionX = (Math.random() * 0.4) - 0.2;
            let directionY = (Math.random() * 0.4) - 0.2;
            particlesArray.push(new Particle(x, y, directionX, directionY, size));
        }
    }

    // Animation loop
    function animate() {
        requestAnimationFrame(animate);
        ctx.clearRect(0, 0, innerWidth, innerHeight);

        for (let i = 0; i < particlesArray.length; i++) {
            particlesArray[i].update();
        }
        connect(); // Call the function to draw lines
    }
    
    // Check distance between particles and draw lines
    function connect() {
        let opacityValue = 1;
        const connectionRadius = 150; // How close particles need to be to connect

        for (let a = 0; a < particlesArray.length; a++) {
            // Connect particles to each other
            for (let b = a; b < particlesArray.length; b++) {
                let distance = ((particlesArray[a].x - particlesArray[b].x) * (particlesArray[a].x - particlesArray[b].x)) +
                               ((particlesArray[a].y - particlesArray[b].y) * (particlesArray[a].y - particlesArray[b].y));
                if (distance < (connectionRadius * connectionRadius)) {
                    opacityValue = 1 - (distance / (connectionRadius * connectionRadius));
                    const isLightTheme = document.body.classList.contains('light-theme');
                    ctx.strokeStyle = isLightTheme ? `rgba(98, 0, 238, ${opacityValue})` : `rgba(187, 134, 252, ${opacityValue})`;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(particlesArray[a].x, particlesArray[a].y);
                    ctx.lineTo(particlesArray[b].x, particlesArray[b].y);
                    ctx.stroke();
                }
            }

            // Connect particles to the mouse
            let mouseDistance = ((particlesArray[a].x - mouse.x) * (particlesArray[a].x - mouse.x)) +
                                ((particlesArray[a].y - mouse.y) * (particlesArray[a].y - mouse.y));
            if (mouseDistance < (mouse.radius * mouse.radius)) {
                opacityValue = 1 - (mouseDistance / (mouse.radius * mouse.radius));
                const isLightTheme = document.body.classList.contains('light-theme');
                ctx.strokeStyle = isLightTheme ? `rgba(98, 0, 238, ${opacityValue})` : `rgba(187, 134, 252, ${opacityValue})`;
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(particlesArray[a].x, particlesArray[a].y);
                ctx.lineTo(mouse.x, mouse.y);
                ctx.stroke();
            }
        }
    }

    init();
    animate();

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            canvas.width = innerWidth;
            canvas.height = innerHeight;
            mouse.radius = (canvas.height / 100) * (canvas.width / 100);
            init();
        }, 250);
    });
    
    // Make mouse leave the screen smoothly
    window.addEventListener('mouseout', () => {
        mouse.x = undefined;
        mouse.y = undefined;
    });
}

function openConfirmModal(modalId) {
    document.getElementById('modal-overlay').classList.add('open');
    document.getElementById(modalId).classList.add('open');
}

function closeConfirmModal() {
    document.getElementById('modal-overlay').classList.remove('open');
    document.querySelectorAll('.modal.open').forEach(modal => modal.classList.remove('open'));
}

function checkConfirmText(inputElement, buttonId) {
    const targetButton = document.getElementById(buttonId);
    if (inputElement.value === 'destroyer_of_worlds') {
        targetButton.disabled = false;
    } else {
        targetButton.disabled = true;
    }
}

// Close modal if overlay is clicked
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeConfirmModal);
    }
});