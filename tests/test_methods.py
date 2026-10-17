"""Synthetic mathematical checks only: no study data or manuscript figures."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
def load(relative):
    spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class SyntheticMethods(unittest.TestCase):
    def test_balanced_variance_closure_and_known_components(self):
        module = load('analysis/02_soc_variance/improved_variance_analysis.py')
        rows=[]
        for a in [-1,1]:
            for b in [-1,1]:
                for c in [-1,1]:
                    rows.append({'A':str(a),'B':str(b),'C':str(c),'y':2*a+3*b+4*c+0.5*a*b+0.2*a*b*c})
        data=pd.DataFrame(rows)
        terms,diag=module.balanced_two_way_ss(data,'y',['A','B','C'],{k:['-1','1'] for k in ['A','B','C']},'SYNTHETIC ONLY')
        self.assertAlmostEqual(terms.SS.sum(),diag['Total_SS'],places=8)
        self.assertAlmostEqual(terms.loc[terms.Term=='A','SS'].iloc[0],32.0,places=8)
        self.assertAlmostEqual(terms.Percent_total_SS.sum(),100.0,places=8)

    def test_linear_shapley_contributions_and_prediction_reconstruction(self):
        module=load('analysis/03_process_models/process_shap_analysis.py')
        class LinearModel:
            def predict(self,data):
                return np.asarray(data) @ np.array([2.0,-3.0])+5.0
        x=np.array([4.0,2.0]); background=np.zeros((3,2))
        phi,pred,base,error=module.mc_shap_one(LinearModel(),x,background,['x1','x2'],np.random.default_rng(42),16)
        np.testing.assert_allclose(phi,[8.,-6.],atol=1e-12)
        self.assertAlmostEqual(pred,base+phi.sum(),places=10)
        self.assertAlmostEqual(error,0.0,places=10)

if __name__=='__main__':unittest.main()
