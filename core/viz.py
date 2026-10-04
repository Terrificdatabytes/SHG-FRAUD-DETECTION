"""Offline-safe Plotly and inline-pyvis visual builders."""
import pandas as pd,plotly.graph_objects as go
from pyvis.network import Network
COLORS={'LOW':'#059669','REVIEW':'#D97706','HIGH':'#DC2626'}
FONT='Inter, Segoe UI, Helvetica, Arial, sans-serif'
def _fit(f,height,legend=True):
    f.update_layout(height=height,autosize=True,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=16,r=24,t=48 if legend else 16,b=20),font=dict(family=FONT,size=13,color='#334155'),showlegend=legend,legend=dict(orientation='h',yanchor='bottom',y=1.03,xanchor='left',x=0,font=dict(size=12)),hoverlabel=dict(bgcolor='white',font=dict(size=12)))
    ax=dict(automargin=True,tickfont=dict(size=12,color='#475569'),title_font=dict(size=12,color='#64748B'),title_standoff=12,linecolor='#E2E8F0',zeroline=False)
    f.update_xaxes(showgrid=False,**ax); f.update_yaxes(gridcolor='#EEF2F7',**ax); return f
def risk_gauge(risk,lo,hi):
    f=go.Figure(go.Indicator(mode='gauge+number',value=risk*100,number={'suffix':'%','font':{'size':40}},gauge={'axis':{'range':[0,100],'tickfont':{'size':12}},'bar':{'color':'#4F46E5','thickness':.28},'borderwidth':0,'steps':[{'range':[0,35],'color':'#D1FAE5'},{'range':[35,72],'color':'#FEF3C7'},{'range':[72,100],'color':'#FEE2E2'}],'threshold':{'line':{'color':'#0F172A','width':3},'value':risk*100}}))
    f.add_annotation(text=f'90% confidence range: {lo:.0%} to {hi:.0%}',x=.5,y=-.02,xref='paper',yref='paper',showarrow=False,font=dict(size=12,color='#64748B'))
    return _fit(f,280,False).update_layout(margin=dict(l=44,r=44,t=24,b=28))
def persistence_diagram(pers):
    x=[p[0] for p in pers] or [0]; y=[p[1] for p in pers] or [0]; mx=max(x+y+[1])
    f=go.Figure([go.Scatter(x=[0,mx],y=[0,mx],mode='lines',name='No loop (birth = death)',line={'dash':'dash','color':'#94A3B8'}),go.Scatter(x=x,y=y,mode='markers',name='Detected loop',marker={'size':13,'color':'#DC2626','line':{'width':2,'color':'white'}})])
    f.update_xaxes(title='Loop appears (time step)'); f.update_yaxes(title='Loop closes (time step)'); return _fit(f,340)
def barcode(pers):
    f=go.Figure()
    for i,(b,d) in enumerate(pers): f.add_trace(go.Scatter(x=[b,d],y=[f'Loop {i+1}']*2,mode='lines+markers',showlegend=False,line={'width':7,'color':'#4F46E5'},marker={'size':9}))
    f.update_xaxes(title='Time step: how long the loop stays open'); f.update_yaxes(title=None); return _fit(f,340,False)
def timeline(records):
    d=pd.DataFrame(records); d['date']=pd.to_datetime(d.date); cr=d[d.direction=='CR']; dr=d[d.direction=='DR']
    f=go.Figure([go.Bar(x=cr.date,y=cr.amount,name='Money in',marker_color='#059669'),go.Bar(x=dr.date,y=-dr.amount,name='Money out',marker_color='#DC2626')])
    f.update_layout(barmode='relative'); f.update_yaxes(title='Rupees (money out shown below zero)',tickformat=','); f.update_xaxes(title=None); return _fit(f,360)
def network_html(top_edges,hub,applicant='Applicant'):
    n=Network(height='500px',width='100%',directed=True,cdn_resources='in_line',bgcolor='#ffffff',font_color='#222222'); n.add_node(applicant,label='Applicant',shape='star',size=30,color='#1565c0')
    for e in top_edges:
        dst='External-'+str(e['dst'])[:4].upper(); n.add_node(dst,label=dst,shape='diamond' if str(e['dst'])==str(hub) else 'dot',size=28 if str(e['dst'])==str(hub) else 16,color='#c62828' if str(e['dst'])==str(hub) else '#9e9e9e'); n.add_edge(applicant,dst,label=f"₹{e['amount']:,.0f}",color='#c62828' if str(e['dst'])==str(hub) else '#78909c',arrows='to',width=2+4*e.get('score',0))
    n.set_options('{"physics":{"barnesHut":{"gravitationalConstant":-9000,"springLength":200,"springConstant":0.02,"avoidOverlap":0.6},"stabilization":{"iterations":150}},"edges":{"font":{"size":13,"align":"middle","strokeWidth":4,"strokeColor":"#ffffff"},"smooth":{"type":"curvedCW","roundness":0.15}},"nodes":{"font":{"size":14}}}'); return n.generate_html()
