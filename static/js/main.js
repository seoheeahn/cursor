let chart;
let currentSymbol = 'MSFT';
let pinnedSymbols = [];

function updateFinancialsTable(data) {
    updateTable('#incomeStatementTable', data.income_statement);
    updateTable('#balanceSheetTable', data.balance_sheet);
    $('#financialDate').text('Data as of: ' + new Date().toLocaleDateString());
}

function updateTable(tableId, data) {
    const tableBody = $(tableId + ' tbody');
    tableBody.empty();
    for (const [key, value] of Object.entries(data)) {
        let formattedValue = value;
        if (typeof value === 'number') {
            if (['EBITDA', 'Total Revenue', 'Market Cap', 'Enterprise Value', 'Total Debt', 'Total Cash'].includes(key)) {
                formattedValue = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
            } else if (['Gross Margins', 'Operating Margins', 'Profit Margins', 'Current Ratio', 'Debt to Equity'].includes(key)) {
                formattedValue = (value * 100).toFixed(2) + '%';
            }
        }
        tableBody.append(`<tr><td>${key}</td><td>${formattedValue}</td></tr>`);
    }
}

function updateNewsContainer(news) {
    const container = $('#newsContainer');
    container.empty();
    news.slice(0, 5).forEach(item => {
        const date = new Date(item.providerPublishTime * 1000);
        container.append(`
            <div class="news-item">
                <img src="${item.thumbnail ? item.thumbnail.resolutions[0].url : 'default_image_url.jpg'}" alt="News Thumbnail">
                <h3>${item.title}</h3>
                <p>${item.publisher}</p>
                <p>${date.toLocaleDateString()} ${date.toLocaleTimeString()}</p>
                <a href="${item.link}" target="_blank">Read more</a>
            </div>
        `);
    });
}

// 나머지 JavaScript 함수들

function updateChart(data) {
    const ohlc = data.price.map((price, index) => [
        Date.parse(data.dates[index]),
        data.open[index],
        data.high[index],
        data.low[index],
        price
    ]);

    const volume = data.volume.map((vol, index) => [
        Date.parse(data.dates[index]),
        vol
    ]);

    Highcharts.stockChart('chart', {
        rangeSelector: { selected: 1 },
        title: { text: currentSymbol + ' Stock Price' },
        yAxis: [{
            labels: { align: 'right', x: -3 },
            title: { text: 'OHLC' },
            height: '60%',
            lineWidth: 2,
            resize: { enabled: true }
        }, {
            labels: { align: 'right', x: -3 },
            title: { text: 'Volume' },
            top: '65%',
            height: '10%',
            offset: 0,
            lineWidth: 2
        }, {
            labels: { align: 'right', x: -3 },
            title: { text: 'MACD' },
            top: '75%',
            height: '10%',
            offset: 0,
            lineWidth: 2
        }, {
            labels: { align: 'right', x: -3 },
            title: { text: 'RSI' },
            top: '85%',
            height: '10%',
            offset: 0,
            lineWidth: 2
        }],
        series: [{
            type: 'candlestick',
            name: currentSymbol,
            data: ohlc,
            tooltip: { valueDecimals: 2 }
        }, {
            type: 'column',
            name: 'Volume',
            data: volume,
            yAxis: 1
        }, {
            type: 'line',
            name: 'SMA 50',
            data: data.sma50.map((value, index) => [Date.parse(data.dates[index]), value]),
            color: 'blue'
        }, {
            type: 'line',
            name: 'SMA 200',
            data: data.sma200.map((value, index) => [Date.parse(data.dates[index]), value]),
            color: 'red'
        }, {
            type: 'macd',
            yAxis: 2,
            name: 'MACD',
            macdLine: {
                styles: { lineColor: 'blue' }
            },
            signalLine: {
                styles: { lineColor: 'red' }
            },
            histogram: {
                styles: { color: 'green' }
            },
            data: data.macd.map((value, index) => [Date.parse(data.dates[index]), value]),
            signalData: data.signal.map((value, index) => [Date.parse(data.dates[index]), value]),
            histogramData: data.macd_histogram.map((value, index) => [Date.parse(data.dates[index]), value])
        }, {
            type: 'line',
            name: 'RSI',
            data: data.rsi.map((value, index) => [Date.parse(data.dates[index]), value]),
            yAxis: 3,
            color: 'purple'
        }]
    });
}

function updateStockSummary(data) {
    const summary = `${currentSymbol} is a ${data.info.sector} company with a market cap of $${(data.info.marketCap / 1e9).toFixed(2)}B. 
                     Its current price is $${data.price[data.price.length - 1].toFixed(2)} with a P/E ratio of ${data.info.trailingPE ? data.info.trailingPE.toFixed(2) : 'N/A'}.`;
    $('#stockSummary').text(summary);
}

function loadData(symbol = 'MSFT') {
    $.ajax({
        url: '/get_data',
        method: 'POST',
        data: { symbol: symbol },
        success: function(data) {
            console.log("Received data:", data);  // 추가된 로그
            if (data.error) {
                $('#errorMessage').text(data.error);
                return;
            }
            $('#errorMessage').text('');
            currentSymbol = symbol;
            updateChart(data);
            updateFinancialsTable(data);
            updateNewsContainer(data.news);
            updateStockSummary(data);
            addToHistory(symbol);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error("AJAX error:", textStatus, errorThrown);  // 추가된 로그
            $('#errorMessage').text('데이터를 가져오는 데 실패했습니다.');
        }
    });
}

function addToHistory(symbol) {
    let history = JSON.parse(localStorage.getItem('stockHistory') || '[]');
    const index = history.indexOf(symbol);
    if (index > -1) {
        history.splice(index, 1);
    }
    history.unshift(symbol);
    if (history.length > 10) history.pop();
    localStorage.setItem('stockHistory', JSON.stringify(history));
    updateHistoryList();
}

function updateHistoryList() {
    const history = JSON.parse(localStorage.getItem('stockHistory') || '[]');
    const historyList = $('#historyList');
    historyList.empty();
    history.forEach(symbol => {
        const isPinned = pinnedSymbols.includes(symbol);
        historyList.append(`
            <li>
                <span onclick="loadData('${symbol}')">${symbol}</span>
                <i class="fas fa-thumbtack ${isPinned ? 'pinned' : ''}" onclick="togglePin('${symbol}')"></i>
                <i class="fas fa-times" onclick="removeFromHistory('${symbol}')"></i>
            </li>
        `);
    });
}

function togglePin(symbol) {
    const index = pinnedSymbols.indexOf(symbol);
    if (index > -1) {
        pinnedSymbols.splice(index, 1);
    } else {
        pinnedSymbols.push(symbol);
    }
    localStorage.setItem('pinnedSymbols', JSON.stringify(pinnedSymbols));
    updateHistoryList();
}

function removeFromHistory(symbol) {
    if (!pinnedSymbols.includes(symbol)) {
        let history = JSON.parse(localStorage.getItem('stockHistory') || '[]');
        history = history.filter(s => s !== symbol);
        localStorage.setItem('stockHistory', JSON.stringify(history));
    }
    updateHistoryList();
}

function refreshAllStocks() {
    const history = JSON.parse(localStorage.getItem('stockHistory') || '[]');
    history.forEach(symbol => loadData(symbol));
}

$(document).ready(function() {
    pinnedSymbols = JSON.parse(localStorage.getItem('pinnedSymbols') || '[]');
    updateHistoryList();
    loadData();

    $('#searchInput').keypress(function(e) {
        if (e.which == 13) {
            loadData($(this).val());
        }
    });

    $('#searchButton').click(function() {
        loadData($('#searchInput').val());
    });

    $('#refreshBtn').click(refreshAllStocks);
});
