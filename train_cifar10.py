import sys
import importlib

import torch
import utils
import matplotlib.pyplot as plt
import resnet

def make_cfg(path):
    mod_name = '.'.join(path.replace('/', '.').split('.')[:-1])
    cfg_lib = importlib.import_module(mod_name)
    return cfg_lib.cfg

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Expect train_cifar10.py [cfg path]")
        exit(1)

    cfg = make_cfg(sys.argv[1])
    model = cfg.arch()
    if cfg.gpu == None:
        model = torch.nn.DataParallel(model)
        model.cuda()
    else:
        model.cuda(cfg.gpu)

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

    criterion = torch.nn.CrossEntropyLoss().cuda()
    optimizer = torch.optim.SGD(model.parameters(), cfg.lr, momentum=cfg.momentum, weight_decay=cfg.weight_decay, nesterov=True)
    train_loader, val_loader = utils.get_cifar10(cfg)

    best_acc = 0
    lrs = []
    losses = []
    accs = []
    macs = []
    for epoch in range(cfg.epochs):
        utils.adjust_lr(optimizer, epoch, cfg.epochs, cfg.lr, warmup_epochs=0)
        utils.train(train_loader, model, criterion, optimizer, epoch, cfg)
        loss, acc = utils.validate(val_loader, model, criterion, cfg)
        lr = optimizer.param_groups[0]['lr']
        lrs.append(lr)
        losses.append(loss)
        accs.append(acc)

        is_best = acc > best_acc
        best_acc = max(acc, best_acc)

        if cfg.gpu == None:
            state_dict = model.module.state_dict()
        else:
            state_dict = model.state_dict()

        state = {
            'epoch': epoch + 1,
            'arch': cfg.arch,
            'state_dict': state_dict,
            'optimizer': optimizer,
            'accs': accs,
            'losses': losses,
            'lrs': lrs,
        }

        torch.save(state, cfg.save_path)

        if is_best:
            best_path = '.'.join(cfg.save_path.split('.')[:-1]) + '.best.pth'
            torch.save(state, best_path)

        print('({:3d}/{:3d}) :: {:.3f}, {:2.2f}'.format(epoch, cfg.epochs, lr, acc))