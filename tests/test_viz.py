from core.viz import risk_gauge,persistence_diagram,network_html
def test_builders(): assert risk_gauge(.5,.3,.7) and persistence_diagram([(0,1)]) and '<html' in network_html([{'dst':'abc','amount':2,'score':1}],'abc').lower()
