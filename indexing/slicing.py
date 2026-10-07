import torch
tensor = torch.ones(4, 4)
tensor[:,1] = 0
print(tensor)