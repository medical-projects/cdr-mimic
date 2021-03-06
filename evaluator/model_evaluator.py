from __future__ import print_function

import torch
import torch.nn as nn
from tqdm import tqdm

import optim

import pdb
import numpy as np

from evaluator.average_meter import AverageMeter


class ModelEvaluator(object):
    """Class for evaluating a model during training."""

    def __init__(self, args, data_loaders, logger, max_eval=None, epochs_per_eval=1):
        """
        Args:
            data_loaders: List of Torch `DataLoader`s to sample from.
            logger: Logger for plotting to console and TensorBoard.
            num_visuals: Number of visuals to display from the validation set.
            max_eval: Maximum number of examples to evaluate at each evaluation.
            epochs_per_eval: Number of epochs between each evaluation.
        """
        self.data_loaders = data_loaders
        self.epochs_per_eval = epochs_per_eval
        self.logger = logger
        self.loss_fn = optim.get_loss_fn(args.loss_fn, args)
        self.max_eval = None if max_eval is None or max_eval < 0 else max_eval
        self.name = args.name
        self.use_intvl = args.use_intvl

    def evaluate(self, model, device, epoch=None):
        """Evaluate a model at the end of the given epoch.

        Args:
            model: Model to evaluate.
            device: Device on which to evaluate the model.
            epoch: The epoch that just finished. Determines whether to evaluate the model.

        Returns:
            metrics: Dictionary of metrics for the current model.

        Notes:
            Returned dictionary will be empty if not an evaluation epoch.
        """
        metrics = {}

        if epoch is None or epoch % self.epochs_per_eval == 0:
            # Evaluate on the training and validation sets
            model.eval()
            for data_loader in self.data_loaders:
                phase_metrics = self._eval_phase(model, data_loader, data_loader.phase, device)
                metrics.update(phase_metrics)
            model.train()

        return metrics

    def _eval_phase(self, model, data_loader, phase, device):
        """Evaluate a model for a single phase.

        Args:
            model: Model to evaluate.
            data_loader: Torch DataLoader to sample from.
            phase: Phase being evaluated. One of 'train', 'val', or 'test'.
            device: Device on which to evaluate the model.

        Returns:
            metrics: Dictionary of metrics for the phase.
        """

        # Keep track of task-specific records needed for computing overall metrics
        records = {'loss_meter': AverageMeter()}

        num_examples = len(data_loader.dataset)
        if self.max_eval is not None:
            num_examples = min(num_examples, self.max_eval)

        # Sample from the data loader and record model outputs
        loss_fn = self.loss_fn
        num_evaluated = 0
        with tqdm(total=num_examples, unit=' ' + phase) as progress_bar:
            for inputs, targets in data_loader:
                if num_evaluated >= num_examples:
                    break

                with torch.no_grad():
                    pred_params = model.forward(inputs.to(device))
                    ages = inputs[:, 1]
                    loss = loss_fn(pred_params, targets.to(device), ages, self.use_intvl)
                    with open(self.name + '_' + phase + '_results.csv', 'ab') as f:
                        np_pred_params = pred_params.data.cpu().numpy()
                        np.savetxt(f, np_pred_params)

                    # # Printing predictions incl. distribution means
                    # for i, params in enumerate(pred_params):
                    #     mu, s = params[0], params[1]
                    #     pred = torch.distributions.LogNormal(mu, s.exp())
                    #     # Write predictions to file
                    #     with open('results.csv', 'a') as f:
                    #         f.write(f'{phase}, {loss}, {mu}, {s}\n')
                    #     #print(f'mu, s: {mu}, {s}\ndist mean: {pred.mean}\ntarget: {targets[i]}')

                self._record_batch(pred_params, loss, **records)

                progress_bar.update(min(inputs.size(0), num_examples - num_evaluated))
                num_evaluated += inputs.size(0)

        # Map to summary dictionaries
        metrics = self._get_summary_dict(phase, **records)

        return metrics

    @staticmethod
    def _record_batch(logits, loss, loss_meter=None):
        """Record results from a batch to keep track of metrics during evaluation.

        Args:
            logits: Batch of logits output by the model.
            loss_meter: AverageMeter keeping track of average loss during evaluation.
        """
        if loss_meter is not None:
            loss_meter.update(loss.item(), logits.size(0))

    @staticmethod
    def _get_summary_dict(phase, loss_meter=None):
        """Get summary dictionaries given dictionary of records kept during evaluation.

        Args:
            phase: Phase being evaluated. One of 'train', 'val', or 'test'.
            loss_meter: AverageMeter keeping track of average loss during evaluation.

        Returns:
            metrics: Dictionary of metrics for the current model.
        """
        metrics = {phase + '_' + 'loss': loss_meter.avg}

        return metrics

    @staticmethod
    def _write_summary_stats(phase, loss_meter=None):
        """Write stats of evaluation to file.

        Args:
            phase: Phase being evaluated. One of 'train', 'val', or 'test'.
            loss_meter: AverageMeter keeping track of average loss during evaluation.

        Returns:
            metrics: Dictionary of metrics for the current model.
        """
        metrics = {phase + '_' + 'loss': loss_meter.avg}

        return metrics
