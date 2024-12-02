class MemoryGame {
    constructor() {
        this.cards = [];
        this.flippedCards = [];
        this.matchedPairs = 0;
        this.moves = 0;
        this.timer = 0;
        this.timerInterval = null;
        this.isPlaying = false;
        
        // Company emojis for cards
        this.emojis = ['🏢', '🏦', '🏪', '🏭', '🏗️', '🏬', '🏣', '🏤'];
        
        this.initializeGame();
        this.setupEventListeners();
    }

    initializeGame() {
        const gameGrid = document.getElementById('gameGrid');
        gameGrid.innerHTML = '';
        this.cards = [...this.emojis, ...this.emojis];
        this.shuffleCards();

        this.cards.forEach((emoji, index) => {
            const card = document.createElement('div');
            card.className = 'card';
            card.dataset.index = index;
            card.innerHTML = `
                <div class="card-front">${emoji}</div>
                <div class="card-back">?</div>
            `;
            gameGrid.appendChild(card);
        });
    }

    shuffleCards() {
        for (let i = this.cards.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [this.cards[i], this.cards[j]] = [this.cards[j], this.cards[i]];
        }
    }

    setupEventListeners() {
        document.getElementById('startGame').addEventListener('click', () => this.startGame());
        document.getElementById('gameGrid').addEventListener('click', (e) => {
            const card = e.target.closest('.card');
            if (card && this.isPlaying) this.flipCard(card);
        });
    }

    startGame() {
        this.isPlaying = true;
        this.moves = 0;
        this.timer = 0;
        this.matchedPairs = 0;
        this.flippedCards = [];
        document.getElementById('moves').textContent = '0';
        document.getElementById('timer').textContent = '0';
        
        clearInterval(this.timerInterval);
        this.timerInterval = setInterval(() => {
            this.timer++;
            document.getElementById('timer').textContent = this.timer;
        }, 1000);

        this.initializeGame();
    }

    flipCard(card) {
        if (
            this.flippedCards.length === 2 || 
            this.flippedCards.includes(card) ||
            card.classList.contains('matched')
        ) return;

        card.classList.add('flipped');
        this.flippedCards.push(card);

        if (this.flippedCards.length === 2) {
            this.moves++;
            document.getElementById('moves').textContent = this.moves;
            this.checkMatch();
        }
    }

    checkMatch() {
        const [card1, card2] = this.flippedCards;
        const match = this.cards[card1.dataset.index] === this.cards[card2.dataset.index];

        if (match) {
            this.matchedPairs++;
            card1.classList.add('matched');
            card2.classList.add('matched');
            this.flippedCards = [];

            if (this.matchedPairs === this.emojis.length) {
                this.gameWon();
            }
        } else {
            setTimeout(() => {
                card1.classList.remove('flipped');
                card2.classList.remove('flipped');
                this.flippedCards = [];
            }, 1000);
        }
    }

    gameWon() {
        clearInterval(this.timerInterval);
        this.isPlaying = false;
        
        const playerName = prompt('Congratulations! Enter your name for the leaderboard:');
        if (playerName) {
            this.saveScore(playerName);
        }
    }

    async saveScore(playerName) {
        try {
            const response = await fetch('/save-score', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: playerName,
                    time: this.timer,
                    moves: this.moves
                })
            });
            
            if (response.ok) {
                this.updateLeaderboard();
            }
        } catch (error) {
            console.error('Error saving score:', error);
        }
    }

    async updateLeaderboard() {
        try {
            const response = await fetch('/leaderboard');
            const scores = await response.json();
            
            const leaderboardBody = document.getElementById('leaderboardBody');
            leaderboardBody.innerHTML = scores
                .map((score, index) => `
                    <tr>
                        <td>${index + 1}</td>
                        <td>${score.name}</td>
                        <td>${score.time}s</td>
                        <td>${score.moves}</td>
                    </tr>
                `)
                .join('');
        } catch (error) {
            console.error('Error updating leaderboard:', error);
        }
    }
}

// Start the game when the page loads
document.addEventListener('DOMContentLoaded', () => {
    const game = new MemoryGame();
    game.updateLeaderboard();
});
