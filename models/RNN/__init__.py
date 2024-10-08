import torch
import torch.nn as nn
from torch.nn import functional as F
from .RecurrentBlock import RecurrentBlock


# generative RNN
class RNN(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.token_embedding = nn.Embedding(config.vocab_size, config.embedding_size)
        self.recurrent_blocks = nn.ModuleList([RecurrentBlock(config) for _ in range(config.n_blocks)])
        self.lm_head = nn.Linear(config.embedding_size, config.vocab_size)
        self.device = config.device

    def forward(self, idx, targets=None):
        x = self.token_embedding(idx)
        B, T, C = x.shape

        # we feed the model one token at a time right bc it can't process everything at once?
        # RNN process things sequentially?
        logits = []
        
        # we don't want to carry over information from completely diff sentences.
        # so reset the hidden states first
        self.reset_recurrent_blocks_hidden_states()

        for t in range(T):
            timestep = x[:, t, :].to(self.device) # B, C
            for rb in self.recurrent_blocks:
                x_timestep = rb(timestep) # B C everytime
            timestep_logits = self.lm_head(x_timestep)
            logits.append(timestep_logits)
        
        logits = torch.stack(logits, dim=1) # B, T, C

        if targets is not None:
            B, T, C = logits.shape
            logits = logits.view(B*T, C)
            targets = targets.view(B*T)
            loss = F.cross_entropy(logits, targets) # default reduce is mean afaik
        else:
            loss=None

        return logits, loss

    def generate(self, idx, max_new_tokens):
        assert max_new_tokens >= 1
        
        # resetting them hidden states
        self.reset_recurrent_blocks_hidden_states()

        # setting up the hidden states
        # intializing using the input string, append the new token (only one)
        logits, loss = self(idx)
        logits = logits[:, -1, :]
        probs = F.softmax(logits, dim=-1)
        idx_next = torch.multinomial(probs, num_samples=1)
        idx = torch.cat((idx, idx_next), dim=1)
        
        # now do the thing over and over again
        for _ in range(max_new_tokens-1):
            # feeding only the last token to generate the next one
            # unlike attention which has to look at the preceeding tokens of context length again
            # representation is already in the hidden states
            logits, loss = self(idx[:, -1:])
            logits = logits[:, -1, :]

            probs = F.softmax(logits, dim=-1)
            idx_next = torch.multinomial(probs, num_samples=1)
            idx = torch.cat((idx, idx_next), dim=1)
        
        return idx
    
    def reset_recurrent_blocks_hidden_states(self):
        for rb in self.recurrent_blocks:
            rb.recurrent.reset_hidden_states()
