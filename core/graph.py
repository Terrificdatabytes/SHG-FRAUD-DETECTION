"""Graph conversion helpers."""
import networkx as nx

def report_graph(df):
    g=nx.DiGraph(); account=str(df.account_id.iloc[0]); g.add_node(account,ntype='member')
    for _,r in df.iterrows():
        cp=str(r.counterparty_id); g.add_node(cp,ntype='external')
        a,b=(cp,account) if r.direction=='CR' else (account,cp)
        if g.has_edge(a,b): g[a][b]['amount']+=float(r.amount)
        else:g.add_edge(a,b,amount=float(r.amount),ts=int(r.date.timestamp()))
    return g,account
