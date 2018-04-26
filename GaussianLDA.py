# coding=utf-8
from __future__ import absolute_import

import torch
from torch import nn
from torch.autograd import Variable
import numpy as np


class GaussianLDA(nn.Module):
    def __init__(self, alpha=30, k=16):
        super(GaussianLDA, self).__init__()
        self.alpha = alpha
        self.K = k

    def forward(self, inputs, targets):
        n = inputs.size(0)
        # Compute pairwise distance
        dist_mat = euclidean_dist(inputs)
        targets = targets.cuda()
        # split the positive and negative pairs
        eyes_ = Variable(torch.eye(n, n)).cuda()
        # eyes_ = Variable(torch.eye(n, n))
        pos_mask = targets.expand(n, n).eq(targets.expand(n, n).t())
        neg_mask = eyes_.eq(eyes_) - pos_mask
        pos_mask = pos_mask - eyes_.eq(1)

        pos_dist = torch.masked_select(dist_mat, pos_mask)
        neg_dist = torch.masked_select(dist_mat, neg_mask)

        num_instances = len(pos_dist)//n + 1
        num_neg_instances = n - num_instances

        pos_dist = pos_dist.resize(len(pos_dist)//(num_instances-1), num_instances-1)
        neg_dist = neg_dist.resize(
            len(neg_dist) // num_neg_instances, num_neg_instances)

        loss = list()
        acc_num = 0

        for i, pos_pair in enumerate(pos_dist):



            pos_pair = torch.sort(pos_pair)[0]
            neg_pair = neg_dist[i]

            pair = torch.cat([pos_pair, neg_pair])
            threshold = torch.sort(pair)[0][self.K]

            pos_neig = torch.masked_select(pos_pair, pos_pair < threshold)
            neg_neig = torch.masked_select(neg_pair, neg_pair < threshold)

            if len(pos_neig) == 0:
                pos_neig = pos_pair[0]

            pos_logit = torch.sum(torch.exp(self.alpha*(1 - pos_neig)))
            neg_logit = torch.sum(torch.exp(self.alpha*(1 - neg_neig)))
            loss_ = -torch.log(pos_logit/(pos_logit + neg_logit))

            if loss_.data[0] < 0.6:
                acc_num += 1
            loss.append(loss_)

        loss = torch.mean(torch.cat(loss))

        accuracy = float(acc_num)/n
        neg_d = torch.mean(neg_dist).data[0]
        pos_d = torch.mean(pos_dist).data[0]

        return loss, accuracy, pos_d, neg_d


def euclidean_dist(inputs_):
    n = inputs_.size(0)
    dist = torch.pow(inputs_, 2).sum(dim=1, keepdim=True).expand(n, n)
    dist = dist + dist.t()
    dist.addmm_(1, -2, inputs_, inputs_.t())
    # for numerical stability
    dist = dist.clamp(min=1e-12).sqrt()
    return dist


def main():
    data_size = 32
    input_dim = 3
    output_dim = 2
    num_class = 4
    # margin = 0.5
    x = Variable(torch.rand(data_size, input_dim), requires_grad=False)
    w = Variable(torch.rand(input_dim, output_dim), requires_grad=True)
    inputs = x.mm(w)
    y_ = 8*list(range(num_class))
    targets = Variable(torch.IntTensor(y_))

    print(GaussianLDA(alpha=30)(inputs, targets))


if __name__ == '__main__':
    main()
    print('Congratulations to you!')
