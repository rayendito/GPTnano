import torch
from models.GPT import GPT
from utils.Tokenizer import Tokenizer
from utils.config import Config
from utils.model_utils import show_parameter_counts

torch.manual_seed(1337)

# variables ==========================================================
data_path = 'input_smaller.txt'

if(torch.cuda.is_available()):
    device = 'cuda'
# elif(torch.backends.mps.is_available()): # MPS currently is still slower than CPUs?
#     device = 'mps'
else:
    device = 'cpu'

# hyperparameters ====================================================
batch_size = 4
max_iters = 1000
eval_interval = 100
eval_iters = 200
lr = 1e-5

# setting up data ====================================================
tokenizer = Tokenizer(data_path, target_vocab_size=356)
all_data_tokenized = tokenizer.encode_from_file(data_path)[0]
train_size = int(0.9*len(all_data_tokenized))

train_data = all_data_tokenized[:train_size]
val_data = all_data_tokenized[train_size:]

# model config =======================================================
config = Config(
    vocab_size=tokenizer.vocab_size,
    context_length=16,
    embedding_size=128,
    n_attn_heads=8,
    n_blocks=6,
    layer_norm_bias=False,
    dropout=0,
    device=device
)

# model and optimizers ===============================================
model = GPT(config).to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr)
show_parameter_counts(model)

# eval helper fucntion ===============================================
def estimate_loss(model, data_train, data_val):
    out = {}
    splits = {'train' : data_train, 'val' : data_val}
    model.eval()
    for split in splits:
        losses = torch.zeros(eval_iters)
        for k in range(eval_iters):
            X, Y = tokenizer.get_batch(splits[split], config.context_length, batch_size)
            X, Y = X.to(device), Y.to(device)
            logits, loss = model(X, Y)
            losses[k] = loss.item()
        out[split] = losses.mean()
    model.train()
    return out

# training loop ======================================================
for it in range(max_iters):
    if(it % eval_interval == 0):
        losses = estimate_loss(model, train_data, val_data)
        print(f"step {it}: train loss {losses['train']:.4f}, val loss {losses['val']:.4f}")

    xb, yb = tokenizer.get_batch(train_data, config.context_length, batch_size)
    xb, yb = xb.to(device), yb.to(device)
    logits, loss = model(xb, yb)
    
    loss.backward()
    optimizer.step()
    
    optimizer.zero_grad(set_to_none = True)

# inference ==========================================================
seed = 'We are accounted poor citizens'
seed_encoded = tokenizer(seed).to(device)
result = model.generate(seed_encoded, 10)
print(tokenizer.decode(result[0]))

