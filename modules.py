def VQVAE1(TRAINDATA,train_loader,dimlatent,noembeddings,learningrate,commitcost):
 """This function trains VQVAE model on the given dataset with the chosen hyperparamters

     Input:
         TRAINDATA (torch tensor_): The training dataset over which the model is trained 
         DATALOADER               : The Dataloader constructed over the training dataset which is used to train the model
         dimlatent (float):       The dimensionality of the latent space that the output of the encoder is transformed into within the VQVAE layer
         noembeddings (float):    The number of embedding vectors which are possible latent space values for each sample
         learningrate (float_):   The learning rate of the VQVAE
         commitcost (float):      The weight in the loss function given to the Mean Squared Error associated with input:Latent Space representation and target: stop gradient function of the encoder output 

     Returns:
         Model()(class)): The trained model
  """
 from torch.utils.data import DataLoader
 import numpy as np
 import torch
 import torch.nn as nn
 import torch.nn.functional as F
 from torch.utils.data.sampler import SubsetRandomSampler
 from torch import flatten
 from torch.nn import ReLU
 
 device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu") #Setting the system so that the device used is GPU
 torch.backends.cudnn.deterministic = True
 torch.backends.cudnn.benchmark = False
 torch.manual_seed(0)
 
 TRAINDATA=TRAINDATA.float()
 



 class indeed(nn.Module):  #Model is created as class 'indeed'
   def __init__(self, numembedding, embeddingdim,commitcost): #initializing the class
        
        super(indeed, self).__init__()
        
        self.numembedding=numembedding #initializing the number of embeddings, the dimensionality of the embeddings and the commitment cost which is used in the loss function
        self.embeddingdim=embeddingdim
        self.commitcost=commitcost
        self.embedding=nn.Embedding(numembedding,embeddingdim)   #setting up the embeddings, where the values in the embedding are sampled from a uniform distribution
        self.embedding.weight.data.uniform_(-2/numembedding, 2/numembedding)

        #Initializing the neural network layers, in this case I created four convolutional neural network layers. I also used Batch Normalization
        self.layer0=nn.Conv2d(3,int(np.ceil(self.embeddingdim/2)),kernel_size=3,stride=1,padding='same')
        self.layer1=nn.BatchNorm2d(int(np.ceil(self.embeddingdim/2)))
        self.layer2=nn.Conv2d(int(np.ceil(self.embeddingdim/2)),int(self.embeddingdim),kernel_size=3,stride=1,padding='same')
        self.layer3=nn.BatchNorm2d(int(self.embeddingdim))
        #The four lines above correspond to the encoder
        
        self.layer4=nn.Conv2d(int(self.embeddingdim),int(np.ceil(self.embeddingdim/2)),kernel_size=3,stride=1,padding='same')
        self.layer5=nn.BatchNorm2d(int(np.ceil(self.embeddingdim/2)))
        self.layer6=nn.Conv2d(int(np.ceil(self.embeddingdim/2)),3,kernel_size=3,stride=1,padding='same')
        #The three lines above correspond to the decoder
        
        
        
   def VQVAE(self,x,numembedding,embeddingdim,commitcost):#Vector Quantization Layer
        x = x.permute(0, 2, 3, 1).contiguous()  #Reshaping the output of the encoder dataset to be "number of images*height*width*channels"
        
        self.embedding.to(device)
        
        flat_x = x.reshape(-1, embeddingdim) #flattening the array so the number of columns correspond to the number of embedding dimensions
        dist=(torch.sum(flat_x**2,dim=1,keepdim=True)+torch.sum(self.embedding.weight**2,dim=1)-2*torch.matmul(flat_x,self.embedding.weight.t())).to(device)
        #The line above calculates the euclidean norm squared with each sample of the flattened output of the encoder with each embedding vector. Wh
        
        indexes=torch.argmin(dist,dim=1).unsqueeze(1) #This determines which embedding vector minimizes euclidean norm between it and each sample of the flattened encoder output
        coded = torch.zeros(indexes.shape[0], self.numembedding, device=x.device)
        coded.scatter_(1,indexes, 1)
        quant=torch.mm(coded, self.embedding.weight).reshape(x.shape)# Array whose rows consist of the minimizing embedding vector for the corresponding sample.This is the latent space representation 

        
        loss = F.mse_loss(quant.detach(), x)+commitcost* F.mse_loss(quant, x.detach()) #non-reconstruction loss part of the loss function
        
        
        quant = x + (quant - x).detach() #straight through estimator of the minimizing embedding vector/latent space representation
        return loss, quant.permute(0, 3, 1, 2).contiguous(),indexes


   
      

   
        
   def forward(self, x):
        
        #This a function which implements the layers
        x=torch.nn.functional.relu(self.layer0(x))
        x=self.layer1(x)
        x=torch.nn.functional.relu(self.layer2(x))
        x=self.layer3(x)
        #The above code corresponds to the encoder
        Loss,z,P=self.VQVAE(x,self.numembedding,self.embeddingdim,self.commitcost) #vector quantization/latent space determining layer
        #The remaining three lines of this function correspond to the decoder
        x=torch.nn.functional.relu(self.layer4(z))
        x=self.layer5(x)
        x=torch.nn.functional.sigmoid(self.layer6(x))
        return x,Loss
        
 model = indeed(numembedding=noembeddings,embeddingdim=dimlatent,commitcost=commitcost)
 model.to(device)
 EPOCHS=30 #number of epochs

 opt = torch.optim.Adam(model.parameters(), lr=learningrate,weight_decay=0.0005) #setting up the optimizer
 lossFn1 = nn.BCELoss(reduction='mean') #setting up the reconstruction loss which is the mean Binary Cross-Entroy


 E=np.empty((EPOCHS))
 E1=np.empty((EPOCHS))
 for e in range(0, EPOCHS): #iterating through the epochs and training the model
  
   
  model.train() #setting the mode to train
    
  totalbinaryentropyloss = 0 #setting the initial values of the reconstruction loss and the non-reconstruction part to 0
  totalnonreconloss=0
 
     # loop over the training set
  for x in train_loader: #looping through the batches
        
        pred,Loss1 = model(x.float().to(device)) #The model is run, and predictions and non-reconstruction loss for the batch are computed
        Loss2=lossFn1(pred.to(device),x.float().to(device)) #calculate reconstruction loss
        loss = Loss1+Loss2 #Calculate total loss as sum of reconstruction and non-reconstruction loss component
        
        opt.zero_grad()   #This line and the next two lines calculating the gradients and updating the weights
        loss.backward()
        opt.step()
        
        totalbinaryentropyloss += len(x)*Loss2*256*256*3 #computing the sum of the reconstruction loss over the batch and adding it to reconstruction loss sum of the previous batches
        totalnonreconloss += len(x)*Loss1*256*256*dimlatent#computing the sum of the reconstruction loss over the batch and adding it to reconstruction loss sum of the previous batches
       
       

   
   

  
 
 
  E1[e]=totalbinaryentropyloss/(np.int64(len(TRAINDATA))*256*256*3) #Computing the mean total binary cross-entropyloss
  
  
  E[e]=totalnonreconloss/(np.int64(len(TRAINDATA))*256*256*dimlatent)+E1[e] # Computing the mean of the total loss
  
 #The remaining code plots the training loss versus the epoch number

 import matplotlib.pyplot as plt
 from matplotlib.pyplot import figure

 ep=range(1,EPOCHS+1)

 plt.plot(ep,E)
 plt.title(f'Average Loss(with Binary Cross-Entropy Reconstruction Loss component) Loss Versus Epoch No for {dimlatent} Dimension Latent Space, {noembeddings} Embeddings, Learning Rate of {learningrate} and {commitcost} Commitment Cost')
 plt.xlabel('Epoch No')
 plt.ylabel('Average  Loss') 
 plt.show()
 plt.plot(ep,E1)
 plt.title(f'Average Binary Cross-Entropy Reconstruction Loss Versus Epoch No for {dimlatent} Dimension Latent Space, {noembeddings} Embeddings, Learning Rate of {learningrate} and {commitcost} Commitment Cost')
 plt.xlabel('Epoch No')
 plt.ylabel('Average Binary Cross-Entropy Loss') 
 plt.show()
 
 return model

def PriorCNN(Encodings,train_loader_1,learningrate,embeddingdim):
 """This function trains a Prior over the embedding vectors using the encodings of the training data

     Input:
         Encodings (torch tensor_): The Encodings (a number which indicate which embedding vector corresponds to each sample) which is one of the outputs of the VQVAE layer. In particular, it is the 'indexes' output of the VQVAE function, within the indeed class in VQVAE1  
         train_loader_1              : The Dataloader constructed over the encodings of the training dataset 
         learning rate: The learning rate used in train the Prior model
         embeddingdim: The size of each embedding vector used in the best model saved in the 'TRAINVALTEST' function in 'train.py'

     Returns:
         Model()(class)): The trained model used to generate a prior. Note, in order to use 'Model' to predict probabilities given some encoding input, softmax still needs to be conducted on the output of Model
  """
 from torch.utils.data import DataLoader
 import numpy as np
 import torch
 import torch.nn as nn
 import torch.nn.functional as F
 from torch.utils.data.sampler import SubsetRandomSampler
 from torch import flatten
 from torch.nn import ReLU
 
 device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu") #Setting the system so that the device used is GPU
 torch.backends.cudnn.deterministic = True
 torch.backends.cudnn.benchmark = False
 torch.manual_seed(0) #setting the random seed
 
 Encodings=Encodings.float()
 



 class indeed(nn.Module):  #Model is created as class 'indeed'
   def __init__(self,embeddingdim): #initializing the class
        
        super(indeed, self).__init__()
        
        self.embeddingdim=embeddingdim
        kernelsize0=5
        kernelsize1=10 
        #Initializing the neural network layers, in this case I created four convolutional neural network layers. I also used Batch Normalization
        self.layer0=nn.Conv2d(embeddingdim,5,kernel_size=kernelsize0,stride=1,padding='same')
        self.masker0=np.zeros((kernelsize0,kernelsize0)) #initializer the masking array
        self.masker0[: kernelsize0//2,:]=1               #allowing the top few rows of the kernel/the rows above a pixel to count towards a pixel's output from this layer
        self.masker0[kernelsize0//2,: kernelsize0//2]=1  #allowing the pixels to the left of, and above a pixel to count towards a pixel's output from this layer
        self.layer1=nn.BatchNorm2d(5)                    #running batch normalization  
        self.layer2=nn.Conv2d(5,embeddingdim,kernel_size=kernelsize1,stride=1,padding='same')
        self.masker1=np.zeros((kernelsize1,kernelsize1)) #This line and the line directly below ensure that the output from the last layer of pixels to left and above the pixels in question can count towards the current pixel's feature map entry
        self.masker1[: kernelsize1//2,:]=1
        self.masker1[kernelsize1//2,: (kernelsize1//2+1)]=1#Allowing the pixels output from the previous layer to count towards the pixel's feature map/output of this layer
                                                           
        self.masker0=torch.tensor(self.masker0).cuda()
        self.masker1=torch.tensor(self.masker1).cuda()
        
        
        
        
   


   
      

   
        
   def forward(self, x):
        x=F.one_hot(x.long(),self.embeddingdim).permute(0, 3, 2, 1)  #converting the encodings (indexes of embedding vector input) into one hot encoded format
        x=x.float()
        
        self.layer0.weight.data=(self.layer0.weight.data*self.masker0).float() #Modifying the kernel of this layer using the mask layer so only the desired pixels contribute towards the output
        #This a function which implements the layers
        x=torch.nn.functional.relu(self.layer0(x))  #Deploying the first CNN layer with rectilinear activation function
        x=self.layer1(x)  #Deploying the batch normalization layer
        self.layer2.weight.data=(self.layer2.weight.data*self.masker1).float()  #Modifying the kernel of this layer using the mask layer so only the desired pixels contribute towards the output
        x=torch.nn.functional.relu(self.layer2(x)) #deploying the second CNN layer with rectilinear activation function
        
        return x
        
 model = indeed(embeddingdim)
 model.to(device)
 EPOCHS=30 #number of epochs

 opt = torch.optim.Adam(model.parameters(), lr=learningrate,weight_decay=0.0005) #setting up the optimizer
 lossFn1 = nn.CrossEntropyLoss(reduction='mean') #setting up the loss function which is the Sparse Categorical Cross-Entroy


 E=np.empty((EPOCHS))
 E1=np.empty((EPOCHS))
 for e in range(0, EPOCHS): #iterating through the epochs and training the model
  print(e)
   
  model.train() #setting the mode to train
    
  totalcrossentropyloss = 0 #setting the initial values of the total loss function to 0
 
 
     # loop over the training set
  for x in train_loader_1: #looping through the batches
        
        pred = model(x.float().to(device))
         #The model is run, and predictions and non-reconstruction loss for the batch are computed
        loss=lossFn1(pred.float().to(device),x.long().to(device)) #calculate reconstruction loss
         #Calculate total loss as sum of reconstruction and non-reconstruction loss component
        
        opt.zero_grad()   #This line and the next two lines calculating the gradients and updating the weights
        loss.backward()
        opt.step()
        
        totalcrossentropyloss += len(x)*loss*256*256 #computing the sum of the loss over the batch and adding it to reconstruction loss sum of the previous batches
        
       

   
   

  
 
 
  E1[e]=totalcrossentropyloss/(np.int64(len(Encodings))*256*256) #Computing the mean total Sparse Categorical Cross-Entropyloss
  
  
  
  
 #The remaining code plots the training loss versus the epoch number

 import matplotlib.pyplot as plt
 from matplotlib.pyplot import figure

 ep=range(1,EPOCHS+1)

 
 plt.plot(ep,E1)
 plt.title(f'Average Binary Cross-Entropy Reconstruction Loss Versus Epoch No  Learning Rate of {learningrate}') 
 plt.ylabel('Average Binary Cross-Entropy Loss') 
 plt.show()
 return(model)
