from numpy.linalg import eigh

from .updates import *


#@autojit
def admm(cumul, prox_fun, X1_0, X4_0, alpha_truth, rho=0.1, alpha=0.99, maxiter=100, positivity=True):
    """
    ADMM framework to minimize a prox-capable objective over the matrix of kernel norms.
    """

    # compute diagA, diagD, O, B and C
    diagA = np.sqrt(cumul.L)
    diagD, O = eigh(cumul.C)
    sqrt_diagD = np.sqrt(diagD)
    B = np.dot(O,np.dot(np.diag(sqrt_diagD),O.T))
    C = np.diag(1. / diagA)

    # initialize parameters
    X1 = X1_0.copy()
    X2 = X1_0.copy()
    X3 = X1_0.copy()
    X4 = X4_0.copy()
    Y1 = np.dot(np.diag(1. / diagA), X1_0)
    #Y1 = X1_0.copy()
    Y2 = np.dot(X4_0, np.dot(O,np.dot(np.diag(1. / sqrt_diagD),O.T)))
    #Y2 = X1_0.copy()
    U1 = np.zeros_like(X1_0)
    U2 = np.zeros_like(X1_0)
    U3 = np.zeros_like(X1_0)
    U4 = np.zeros_like(X1_0)
    U5 = np.zeros_like(X1_0)

    for _ in range(maxiter):
        X1[:] = update_X1(prox_fun, X2, Y1, U2, U4, diagA, rho=rho)
        X2[:] = update_X2(X1, X3, U2, U3, positivity)
        X3[:] = update_X3(X2, U3, alpha=alpha)
        X4[:] = update_X4(Y2, U5, B)
        Y1[:] = update_Y1(X1, Y2, U1, U4, diagA, C)
        Y2[:] = update_Y2(X4, Y1, U1, U5, sqrt_diagD, O, B, C)
        U1[:] = update_U1(U1, Y1, Y2, C)
        U2[:] = update_U2(U2, X1, X2)
        U3[:] = update_U3(U3, X2, X3)
        U4[:] = update_U4(U4, X1, Y1, diagA)
        U5[:] = update_U5(U5, X4, Y2, B)

#    print("||X1 - X_2|| = ", np.linalg.norm(X1-X2))
#    print("||X2 - X_3|| = ", np.linalg.norm(X2-X3))
#    print("||U1|| = ", np.linalg.norm(U1))
#    print("||U2|| = ", np.linalg.norm(U2))
#    print("||U3|| = ", np.linalg.norm(U3))
#    print("||U4|| = ", np.linalg.norm(U4))
#    print("||U5|| = ", np.linalg.norm(U5))

    return .5*(X1+X1.T)

if __name__ == "__main__":
    import numpy as np
    from mlpp.hawkesnoparam.estim import Estim
    import mlpp.pp.hawkes as hk
    import simulation as simu

    d = 2
    mu = np.array([0.2, 0.3])
    mus = simu.simulate_mu(d, mu=mu)
    Alpha_truth = np.array(
    [[0.7, 0.3],
    [0.5, 0.2]])
    Beta = 0.2 * np.ones((d,d))

    kernels = [[hk.HawkesKernelExp(a, b) for (a, b) in zip(a_list, b_list)] for (a_list, b_list) in zip(Alpha_truth, Beta)]
    h = hk.Hawkes(kernels=kernels, mus=list(mus))
    h.simulate(10000)
    estim = Estim(h, n_threads=8)

    from utils import prox

    X0 = np.eye(d)
    #X0 = np.ones(d**2).reshape(d,d)
    rho = 0.01
    maxiter = 1000

    # main step
    X_ = admm(estim, prox.sq_frob, X0, X0, Alpha_truth, rho=rho, maxiter=maxiter)