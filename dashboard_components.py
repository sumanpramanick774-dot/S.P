"""
Plotly Chart Builders and Styled UI Elements for Desktop and Mobile.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def build_candlestick_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Builds interactive intraday chart with EMA20 and EMA50 overlays."""
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='5m Price',
        increasing_line_color='#00FFA3',
        decreasing_line_color='#FF4976'
    ))
    
    if 'ema20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ema20'],
            mode='lines', name='EMA 20',
            line=dict(color='#FFD700', width=1.5)
        ))
        
    if 'ema50' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['ema50'],
            mode='lines', name='EMA 50',
            line=dict(color='#00BFFF', width=1.5)
        ))
        
    fig.update_layout(
        title=f"<b>{symbol}</b> - 5-Minute Intraday Structure",
        template="plotly_dark",
        paper_bgcolor="#1A1D24",
        plot_bgcolor="#1A1D24",
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=50, b=40),
        height=450
    )
    return fig

def build_rsi_chart(df: pd.DataFrame) -> go.Figure:
    """Builds clean RSI oscillator chart with 30, 50, 70 lines."""
    fig = go.Figure()
    
    if 'rsi14' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['rsi14'],
            line=dict(color='#B388FF', width=1.5),
            name='RSI (14)'
        ))
        
    fig.add_hline(y=70, line_dash="dash", line_color="#FF4976", annotation_text="Overbought 70")
    fig.add_hline(y=50, line_dash="dot", line_color="#888888")
    fig.add_hline(y=30, line_dash="dash", line_color="#00FFA3", annotation_text="Oversold 30")
    
    fig.update_layout(
        title="Relative Strength Index (RSI 14)",
        template="plotly_dark",
        paper_bgcolor="#1A1D24",
        plot_bgcolor="#1A1D24",
        yaxis=dict(range=[0, 100]),
        margin=dict(l=40, r=40, t=50, b=40),
        height=220
    )
    return fig

def format_cell_state(val: str) -> str:
    """Returns CSS background highlighting for classification grids."""
    colors = {
        "ABOVE": "background-color: #005F40; color: #FFFFFF; font-weight: bold;",
        "BELOW": "background-color: #6B1D2F; color: #FFFFFF; font-weight: bold;",
        "NEUTRAL": "background-color: #404040; color: #E0E0E0;",
        "MISSING DATA": "background-color: #2D3139; color: #FF9800; font-style: italic;"
    }
    return colors.get(val, "")

