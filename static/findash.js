let tickers = [];
let selectedTickers = [];

// Carregar tickers do servidor
function loadTickers(selectElement) {
    fetch('/get-tickers')
        .then(response => response.json())
        .then(data => {
            tickers = data;
            updateTickerOptions(selectElement);
        })
        .catch(error => console.error('Erro ao carregar tickers:', error));
}

// Atualizar opções de tickers na dropdown
function updateTickerOptions(selectElement) {
    selectElement.innerHTML = '<option value="" disabled selected>Selecione um ticker</option>';
    tickers.forEach(ticker => {
        if (!selectedTickers.includes(ticker.symbol)) {
            const option = document.createElement('option');
            option.value = ticker.symbol;
            option.textContent = `${ticker.symbol} - ${ticker.name}`;
            selectElement.appendChild(option);
        }
    });
}

// Adicionar ticker selecionado à lista
function addSelectedTicker(selectElement) {
    const tickerSymbol = selectElement.value;
    if (!tickerSymbol || selectedTickers.includes(tickerSymbol)) return;

    selectedTickers.push(tickerSymbol);
    updateTickerOptions(selectElement);

    const selectedTickersDiv = document.getElementById('selected-tickers');
    const ticker = tickers.find(t => t.symbol === tickerSymbol);
    const tickerDiv = document.createElement('div');
    tickerDiv.dataset.symbol = tickerSymbol;
    tickerDiv.className = 'd-flex align-items-center gap-2 mb-2';
    tickerDiv.innerHTML = `
        <span>${ticker.symbol} - ${ticker.name}</span>
        
        <!-- Forma 100% acessível e semântica -->
        <label class="d-flex align-items-center gap-2">
            <span class="visually-hidden">Quantidade para ${ticker.symbol}</span>
            <input 
                type="number" 
                name="quantities[]" 
                min="1" 
                value="1" 
                onchange="updateQuantity(this, '${tickerSymbol}')" 
                class="form-control" 
                style="width: 80px;"
                data-symbol="${tickerSymbol}"
            >
        </label>

        <button type="button" onclick="removeTicker('${tickerSymbol}')" class="btn btn-danger btn-sm">Remover</button>
        <input type="hidden" name="tickers[]" value="${tickerSymbol}">
    `;


    selectedTickersDiv.appendChild(tickerDiv);

    selectElement.value = ''; // Resetar a dropdown
}

// Atualizar quantidade no input hidden
function updateQuantity(inputElement, tickerSymbol) {
    const quantity = inputElement.value;
    const hiddenInput = document.querySelector(`.quantity-input[data-symbol="${tickerSymbol}"]`);
    if (hiddenInput) {
        hiddenInput.value = quantity;
    }
}

// Remover ticker da lista
function removeTicker(tickerSymbol) {
    selectedTickers = selectedTickers.filter(t => t !== tickerSymbol);
    const tickerDiv = document.querySelector(`div[data-symbol="${tickerSymbol}"]`);
    if (tickerDiv) {
        tickerDiv.remove();
    }
    const select = document.querySelector('.ticker-select');
    updateTickerOptions(select);
}

// Format date as YYYY-MM-DD
function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// Atualizar datas com base no período selecionado
function updateDates() {
    const period = document.querySelector('input[name="period"]:checked').value;
    const endDateInput = document.getElementById('end_date');
    const startDateInput = document.getElementById('start_date');

    let endDate;
    if (endDateInput.value && !isNaN(new Date(endDateInput.value).getTime())) {
        endDate = new Date(endDateInput.value);
    } else {
        endDate = new Date();
        endDate.setDate(endDate.getDate() - 1); // Ontem
        endDateInput.value = formatDate(endDate);
    }

    if (period !== 'custom') {
        const startDate = new Date(endDate);
        if (period === '0.5') {
            startDate.setMonth(endDate.getMonth() - 6); // Subtrair 6 meses
        } else {
            const years = parseInt(period);
            startDate.setFullYear(endDate.getFullYear() - years); // Subtrair 1 ou 5 anos
        }
        startDateInput.value = formatDate(startDate);
    }
}

// Marcar período como personalizado quando as datas são alteradas manualmente
function setCustomPeriod() {
    const customRadio = document.getElementById('custom-period');
    customRadio.checked = true;
}

// Inicializar
document.addEventListener('DOMContentLoaded', () => {
    const initialSelect = document.querySelector('.ticker-select');
    loadTickers(initialSelect);
    updateDates(); // Preencher datas iniciais com 6 meses por padrão
});