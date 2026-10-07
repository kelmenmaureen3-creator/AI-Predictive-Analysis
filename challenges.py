import torch
tensor=torch.rand(6,6)
print(tensor.shape)
print(tensor.dtype)
tensor[0,:] = 0
print(tensor)
tensor[:,-1] = 1
print(tensor)
total_sum = torch.sum(tensor)
print(total_sum)
average = torch.mean(tensor)
tensormax = torch.max(tensor)
tensormin = torch.min(tensor)   
print(f"Average: {average}, Max: {tensormax}, Min: {tensormin}")
tensor_int=tensor.int()
print(tensor_int)